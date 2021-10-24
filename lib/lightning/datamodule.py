from argparse import ArgumentParser
from pathlib import Path

import pytorch_lightning as pl
from sklearn.model_selection import train_test_split
from torch import Tensor
from torch.utils.data import DataLoader
from torchvision import transforms

from lib import dataset
from lib.dataset import StylizationDataset, files_in, EndlessDataset


class DataModule(pl.LightningDataModule):
    @staticmethod
    def add_argparse_args(parent_parser):
        parser = ArgumentParser(parents=[parent_parser], add_help=False)
        parser.add_argument('--content', type=str, default=r'C:\[Datasets]\MSCOCO\train2017')
        parser.add_argument('--style', type=str, default=r'C:\[Datasets]\WikiArt\train')
        parser.add_argument('--test-content', type=str)
        parser.add_argument('--test-style', type=str)
        parser.add_argument('--batch-size', type=int, default=8)

        return parser

    def __init__(self, content, style, batch_size, test_content=None, test_style=None, **_):
        super().__init__()

        content_files, test_content_files = self.get_files(content, test_content, batch_size)
        style_files, test_style_files = self.get_files(style, test_style, batch_size)

        train_transforms = self.train_transforms()
        self.train_dataset = StylizationDataset(content_files, style_files,
                                                style_transform=train_transforms['style'],
                                                content_transform=train_transforms['content'])

        test_transforms = self.test_transforms()
        self.test_dataset = EndlessDataset(test_content_files, test_style_files,
                                           style_transform=test_transforms['style'],
                                           content_transform=test_transforms['content'])

        self.batch_size = batch_size
        self.test_batch_size = min(len(test_content_files), len(test_style_files), batch_size)

    def train_transforms(self):
        return {
            'content': transforms.Compose([
                transforms.Resize(size=(512, 512)),
                transforms.RandomCrop(256),
                transforms.ToTensor(),
            ]),
            'style': transforms.Compose([
                transforms.Resize(size=(512, 512)),
                transforms.RandomCrop(256),
                transforms.ToTensor(),
            ])
        }

    def test_transforms(self):
        return {
            'content': transforms.Compose([
                # Batched images must have same size
                # CenterCrop gives better impression how full image lib will look like
                transforms.CenterCrop(size=(256, 256)),
                # Add base transforms
                dataset.content_transforms(),
            ]),
            'style': transforms.Compose([
                # Add base transforms
                dataset.style_transforms(),
            ])
        }

    def train_dataloader(self):
        return DataLoader(self.train_dataset, batch_size=self.batch_size)

    def val_dataloader(self):
        return DataLoader(self.test_dataset, batch_size=self.test_batch_size)

    def test_dataloader(self):
        return DataLoader(self.test_dataset, batch_size=self.test_batch_size)

    def transfer_batch_to_device(self, batch, device):
        for k, v in batch.items():
            if isinstance(v, Tensor):
                batch[k] = v.to(device)
        return batch

    def prepare_data(self):
        pass

    def setup(self, stage=None):
        pass

    @staticmethod
    def get_files(train_path, test_path, batch_size):
        train_files = files_in(train_path)

        if test_path is None:
            train_files, test_files = train_test_split(train_files, test_size=batch_size)
        else:
            if Path(test_path).is_dir():
                test_files = files_in(test_path)
            else:
                test_files = [test_path]
        return train_files, test_files
