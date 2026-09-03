import math

import torch
import torch.nn as nn


class PositionalEncoding(nn.Module):
    """
    Transformer用の位置エンコーディング。
    """

    def __init__(
        self,
        d_model,
        max_len=500,
    ):
        super().__init__()

        position = torch.arange(
            max_len,
            dtype=torch.float32
        ).unsqueeze(1)

        div_term = torch.exp(
            torch.arange(
                0,
                d_model,
                2,
                dtype=torch.float32
            )
            * (
                -math.log(10000.0)
                / d_model
            )
        )

        pe = torch.zeros(
            max_len,
            d_model
        )

        pe[:, 0::2] = torch.sin(
            position * div_term
        )

        pe[:, 1::2] = torch.cos(
            position * div_term
        )

        pe = pe.unsqueeze(0)

        self.register_buffer(
            "pe",
            pe
        )

    def forward(self, x):

        return (
            x
            + self.pe[:, :x.size(1)]
        )


class TrajectoryTransformer(
    nn.Module
):
    """
    過去の車両軌跡から未来の車両軌跡を予測するTransformer。
    """

    def __init__(
        self,
        input_dim=5,
        d_model=128,
        nhead=8,
        num_layers=4,
        dim_feedforward=256,
        dropout=0.1,
        pred_len=10,
    ):

        super().__init__()

        self.pred_len = pred_len

        # ---------------------------------------------
        # 入力特徴量
        # ---------------------------------------------

        self.input_projection = nn.Linear(
            input_dim,
            d_model
        )

        # ---------------------------------------------
        # Positional Encoding
        # ---------------------------------------------

        self.positional_encoding = (
            PositionalEncoding(
                d_model
            )
        )

        # ---------------------------------------------
        # Transformer Encoder
        # ---------------------------------------------

        encoder_layer = (
            nn.TransformerEncoderLayer(
                d_model=d_model,
                nhead=nhead,
                dim_feedforward=dim_feedforward,
                dropout=dropout,
                batch_first=True,
                norm_first=True,
            )
        )

        self.transformer = (
            nn.TransformerEncoder(
                encoder_layer,
                num_layers=num_layers,
            )
        )

        # ---------------------------------------------
        # 出力
        # ---------------------------------------------

        self.output_layer = nn.Sequential(
            nn.Linear(
                d_model,
                d_model
            ),
            nn.ReLU(),
            nn.Linear(
                d_model,
                pred_len * 2
            )
        )

    def forward(self, x):
        """
        Parameters
        ----------
        x : Tensor
            [batch, seq_len, 5]

        Returns
        -------
        Tensor
            [batch, pred_len, 2]
        """

        # [B, seq_len, 5]
        x = self.input_projection(
            x
        )

        # [B, seq_len, d_model]
        x = self.positional_encoding(
            x
        )

        # [B, seq_len, d_model]
        x = self.transformer(
            x
        )

        # 最後の時刻
        x = x[:, -1, :]

        # [B, pred_len * 2]
        x = self.output_layer(
            x
        )

        # [B, pred_len, 2]
        x = x.reshape(
            x.size(0),
            self.pred_len,
            2
        )

        return x