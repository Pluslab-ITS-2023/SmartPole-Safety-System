# -*- coding: UTF-8 -*-

import math

import torch
import torch.nn as nn


class PositionalEncoding(nn.Module):
    """
    Transformer用の位置エンコーディング
    """

    def __init__(
        self,
        d_model: int,
        max_len: int = 500
    ) -> None:
        super().__init__()

        position = torch.arange(max_len).unsqueeze(1)

        div_term = torch.exp(
            torch.arange(0, d_model, 2)
            * (-math.log(10000.0) / d_model)
        )

        pe = torch.zeros(max_len, d_model)

        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)

        pe = pe.unsqueeze(0)

        self.register_buffer("pe", pe)

    def forward(
        self,
        x: torch.Tensor
    ) -> torch.Tensor:
        """
        Args:
            x:
                [batch_size, sequence_length, d_model]

        Returns:
            [batch_size, sequence_length, d_model]
        """

        return x + self.pe[:, :x.size(1)]


class FrontVehicleAttention(nn.Module):
    """
    自車から周辺車両へのCross Attention

    前方車両に対してAttention biasを加える。
    """

    def __init__(
        self,
        d_model: int,
        nhead: int,
        front_attention_bias: float = 1.0
    ) -> None:
        super().__init__()

        if d_model % nhead != 0:
            raise ValueError(
                "d_model must be divisible by nhead."
            )

        self.d_model = d_model
        self.nhead = nhead
        self.head_dim = d_model // nhead

        self.query_projection = nn.Linear(
            d_model,
            d_model
        )

        self.key_projection = nn.Linear(
            d_model,
            d_model
        )

        self.value_projection = nn.Linear(
            d_model,
            d_model
        )

        self.output_projection = nn.Linear(
            d_model,
            d_model
        )

        # 前方車両に与えるAttention bias
        self.front_attention_bias = front_attention_bias

    def forward(
        self,
        ego: torch.Tensor,
        neighbors: torch.Tensor,
        front_mask: torch.Tensor,
        neighbor_mask: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """
        Args:
            ego:
                [B, T, D]

            neighbors:
                [B, T, K, D]

            front_mask:
                [B, T, K]
                前方車両ならTrue

            neighbor_mask:
                [B, T, K]
                有効な周辺車両ならTrue

        Returns:
            context:
                [B, T, D]

            attention_weights:
                [B, H, T, K]
        """

        batch_size, sequence_length, d_model = ego.shape
        max_neighbors = neighbors.size(2)

        # Query
        query = self.query_projection(ego)

        # Key / Value
        key = self.key_projection(neighbors)
        value = self.value_projection(neighbors)

        # --------------------------------------------------
        # Headに分割
        #
        # query:
        # [B, T, D]
        # ↓
        # [B, H, T, head_dim]
        #
        # key/value:
        # [B, T, K, D]
        # ↓
        # [B, H, T, K, head_dim]
        # --------------------------------------------------

        query = query.view(
            batch_size,
            sequence_length,
            self.nhead,
            self.head_dim
        ).permute(0, 2, 1, 3)

        key = key.view(
            batch_size,
            sequence_length,
            max_neighbors,
            self.nhead,
            self.head_dim
        ).permute(0, 3, 1, 2, 4)

        value = value.view(
            batch_size,
            sequence_length,
            max_neighbors,
            self.nhead,
            self.head_dim
        ).permute(0, 3, 1, 2, 4)

        # --------------------------------------------------
        # Attention score
        #
        # [B, H, T, 1, D]
        # ×
        # [B, H, T, D, K]
        #
        # → [B, H, T, 1, K]
        # --------------------------------------------------

        query = query.unsqueeze(-2)

        key = key.transpose(-2, -1)

        attention_scores = torch.matmul(
            query,
            key
        ).squeeze(-2)

        attention_scores = (
            attention_scores
            / math.sqrt(self.head_dim)
        )

        # --------------------------------------------------
        # 前方車両Attention bias
        # --------------------------------------------------

        front_bias = (
            front_mask
            .float()
            * self.front_attention_bias
        )

        # [B, T, K]
        # ↓
        # [B, 1, T, K]

        front_bias = front_bias.unsqueeze(1)

        attention_scores = (
            attention_scores
            + front_bias
        )

        # --------------------------------------------------
        # 存在しない車両はAttention対象から除外
        # --------------------------------------------------

        attention_scores = attention_scores.masked_fill(
            ~neighbor_mask.unsqueeze(1),
            float("-inf")
        )

        # --------------------------------------------------
        # Softmax
        # --------------------------------------------------

        attention_weights = torch.softmax(
            attention_scores,
            dim=-1
        )

        # --------------------------------------------------
        # Valueとの加重和
        # --------------------------------------------------

        value = value

        attention_output = torch.matmul(
            attention_weights.unsqueeze(-2),
            value
        ).squeeze(-2)

        # [B, H, T, head_dim]
        # ↓
        # [B, T, D]

        attention_output = attention_output.permute(
            0,
            2,
            1,
            3
        ).contiguous()

        attention_output = attention_output.view(
            batch_size,
            sequence_length,
            d_model
        )

        attention_output = self.output_projection(
            attention_output
        )

        return attention_output, attention_weights


class TrajectoryTransformer(nn.Module):
    """
    周辺車両および前方車両Attentionを利用した
    軌跡予測Transformer

    入力：
        自車の過去軌跡
        周辺車両の情報

    出力：
        未来のx, y
    """

    def __init__(
        self,
        ego_dim: int = 5,
        neighbor_dim: int = 6,
        d_model: int = 128,
        nhead: int = 8,
        num_layers: int = 4,
        dim_feedforward: int = 256,
        dropout: float = 0.1,
        pred_len: int = 50,
        front_attention_bias: float = 1.0
    ) -> None:
        super().__init__()

        self.pred_len = pred_len
        self.d_model = d_model

        # ==============================================
        # 自車Embedding
        # ==============================================

        self.ego_embedding = nn.Linear(
            ego_dim,
            d_model
        )

        # ==============================================
        # 周辺車両Embedding
        # ==============================================

        self.neighbor_embedding = nn.Linear(
            neighbor_dim,
            d_model
        )

        # ==============================================
        # 前方車両Attention
        # ==============================================

        self.front_attention = FrontVehicleAttention(
            d_model=d_model,
            nhead=nhead,
            front_attention_bias=front_attention_bias
        )

        # ==============================================
        # 自車 + 周辺車両の融合
        # ==============================================

        self.fusion = nn.Sequential(
            nn.Linear(
                d_model * 2,
                d_model
            ),
            nn.ReLU(),
            nn.Dropout(dropout)
        )

        # ==============================================
        # Temporal Transformer
        # ==============================================

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
            batch_first=True,
            norm_first=True
        )

        self.encoder = nn.TransformerEncoder(
            encoder_layer,
            num_layers=num_layers
        )

        self.positional_encoding = PositionalEncoding(
            d_model=d_model,
            max_len=500
        )

        # ==============================================
        # 未来時刻Embedding
        # ==============================================

        self.future_time_embedding = nn.Sequential(
            nn.Linear(1, d_model),
            nn.ReLU(),
            nn.Linear(d_model, d_model)
        )

        # ==============================================
        # Future Decoder
        # ==============================================

        decoder_layer = nn.TransformerDecoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
            batch_first=True,
            norm_first=True
        )

        self.decoder = nn.TransformerDecoder(
            decoder_layer,
            num_layers=num_layers
        )

        # ==============================================
        # x, y 出力
        # ==============================================

        self.output_layer = nn.Sequential(
            nn.Linear(
                d_model,
                d_model
            ),
            nn.ReLU(),
            nn.Linear(
                d_model,
                2
            )
        )

    def forward(
        self,
        ego: torch.Tensor,
        neighbors: torch.Tensor,
        front_mask: torch.Tensor,
        neighbor_mask: torch.Tensor,
        future_times: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """
        Args:
            ego:
                [B, T, ego_dim]

            neighbors:
                [B, T, K, neighbor_dim]

            front_mask:
                [B, T, K]

            neighbor_mask:
                [B, T, K]

            future_times:
                [B, P]

        Returns:
            predictions:
                [B, P, 2]

            attention_weights:
                [B, H, T, K]
        """

        # ==============================================
        # 自車Embedding
        # ==============================================

        ego_feature = self.ego_embedding(ego)

        # ==============================================
        # 周辺車両Embedding
        # ==============================================

        neighbor_feature = self.neighbor_embedding(
            neighbors
        )

        # ==============================================
        # 前方車両Attention
        # ==============================================

        neighbor_context, attention_weights = (
            self.front_attention(
                ego_feature,
                neighbor_feature,
                front_mask,
                neighbor_mask
            )
        )

        # ==============================================
        # 自車 + 周辺車両
        # ==============================================

        fused = torch.cat(
            [
                ego_feature,
                neighbor_context
            ],
            dim=-1
        )

        fused = self.fusion(fused)

        # ==============================================
        # 時系列Transformer
        # ==============================================

        fused = self.positional_encoding(
            fused
        )

        memory = self.encoder(
            fused
        )

        # ==============================================
        # 最後の時刻の状態
        # ==============================================

        current_state = memory[:, -1:, :]

        # ==============================================
        # Future Query
        # ==============================================

        future_times = future_times.unsqueeze(-1)

        future_query = self.future_time_embedding(
            future_times
        )

        # ==============================================
        # Decoder
        # ==============================================

        decoder_output = self.decoder(
            future_query,
            memory
        )

        # ==============================================
        # x, y
        # ==============================================

        predictions = self.output_layer(
            decoder_output
        )

        return predictions, attention_weights
        