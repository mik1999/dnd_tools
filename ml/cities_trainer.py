import pytorch_lightning as pl
import typing
from deeppavlov.core.data.simple_vocab import SimpleVocabulary
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.utils.data as td


SPECIAL_TOKENS = ['<PAD>', '<UNK>', '<BEGIN>', '<END>']


class CharLangData(pl.LightningDataModule):
    def __init__(self, data: typing.List[str]):
        super().__init__()

        self.vocab = SimpleVocabulary(
            special_tokens=tuple(*SPECIAL_TOKENS),
            save_path='./data',
            unk=-1,
            pad_with_zeros=False,
            unk_token='<UNK>',
        )

        self.train_data = train_data
        self.val_data = val_data
        self.test_data = test_data

    def prepare_data(self):
        self.test_data = self.test_data.assign(rdm=np.random.random(len(self.test_data))).assign(
            avg=self.train_data["time"].mean())

    def setup(self, stage=None):
        if stage == "fit" or stage is None:
            self.train_dataset = td.TensorDataset(
                torch.from_numpy(self.train_data[self.features].values),
                torch.from_numpy(self.train_data["time"].values)
            )

            self.val_dataset = td.TensorDataset(
                torch.from_numpy(self.val_data[self.features].values),
                torch.from_numpy(self.val_data["time"].values)
            )

        if stage == "test" or stage is None:
            self.test_dataset = td.TensorDataset(
                torch.from_numpy(self.test_data[self.features].values),
                torch.from_numpy(self.test_data[["time", "avg", "rdm"]].values)
            )

    def train_dataloader(self):
        return td.DataLoader(self.train_dataset, batch_size=2048, shuffle=True, num_workers=0)

    def val_dataloader(self):
        return td.DataLoader(self.val_dataset, batch_size=2048, num_workers=0)

    def test_dataloader(self):
        return td.DataLoader(self.test_dataset, batch_size=512, shuffle=False, num_workers=0)
