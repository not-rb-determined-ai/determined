from typing import Any, Dict
import os
import filelock
from attrdict import AttrDict
import torch
import torchvision
import torchvision.transforms as transforms
import deepspeed
from deepspeed.pipe import PipelineModule
from alexnet import AlexNet

from determined.pytorch import DataLoader
from determined.pytorch.deepspeed import (
    DeepSpeedMPU,
    DeepSpeedTrial,
    DeepSpeedTrialContext,
    overwrite_deepspeed_config,
)


def join_layers(vision_model):
    layers = [
        *vision_model.features,
        vision_model.avgpool,
        lambda x: torch.flatten(x, 1),
        *vision_model.classifier,
    ]
    return layers


class BatchDataset(torch.utils.data.Dataset):
    def __init__(self, batch):
        self.images = batch[0]
        self.labels = batch[1]

    def __getitem__(self, idx):
        return [self.images[idx], self.labels[idx]]

    def __len__(self):
        return len(self.images)


class CIFARTrial(DeepSpeedTrial):
    def __init__(self, context: DeepSpeedTrialContext) -> None:
        self.context = context
        self.args = AttrDict(self.context.get_hparams())
        model = AlexNet(10)
        model = PipelineModule(
            layers=join_layers(model),
            loss_fn=torch.nn.CrossEntropyLoss(),
            num_stages=self.args.pipe_parallel_size,
            partition_method=self.args.part,
            activation_checkpoint_interval=0,
        )

        ds_config = overwrite_deepspeed_config(
            self.args.deepspeed_config, self.args.get("overwrite_deepspeed_args", {})
        )
        model_engine, optimizer, _, _ = deepspeed.initialize(
            args=self.args,
            model=model,
            model_parameters=[p for p in model.parameters() if p.requires_grad],
            config=ds_config,
        )

        self.model_engine = model_engine
        self.model_engine = self.context.wrap_model_engine(model_engine)
        self.context.wrap_mpu(DeepSpeedMPU(model_engine.mpu))

    def train_batch(
        self, iter_dataloader, epoch_idx: int, batch_idx: int
    ) -> Dict[str, torch.Tensor]:
        loss = self.model_engine.train_batch(iter_dataloader)
        return {"loss": float(loss)}

    def evaluate_batch(self, iter_dataloader, batch_idx) -> Dict[str, Any]:
        """
        Calculate validation metrics for a batch and return them as a dictionary.
        This method is not necessary if the user defines evaluate_full_dataset().
        """
        loss = self.model_engine.eval_batch(iter_dataloader)
        return {"loss": loss}

    def build_training_data_loader(self) -> Any:
        transform = transforms.Compose(
            [
                transforms.Resize(256),
                transforms.CenterCrop(224),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]
                ),
            ]
        )

        with filelock.FileLock(os.path.join("/tmp", "train.lock")):
            trainset = torchvision.datasets.CIFAR10(
                root="/data", train=True, download=True, transform=transform
            )

        return DataLoader(
            trainset,
            batch_size=self.context.train_micro_batch_size_per_gpu,
            shuffle=True,
            num_workers=2,
            drop_last=True,
        )

    def build_validation_data_loader(self) -> Any:
        transform = transforms.Compose(
            [
                transforms.Resize(256),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]
                ),
            ]
        )

        with filelock.FileLock(os.path.join("/tmp", "val.lock")):
            testset = torchvision.datasets.CIFAR10(
                root="/data", train=False, download=True, transform=transform
            )

        return DataLoader(
            testset,
            batch_size=self.context.train_micro_batch_size_per_gpu,
            shuffle=False,
            num_workers=2,
            drop_last=True,
        )
