# type: ignore
import copy
import os
import pathlib
from typing import Any, Dict, Optional

import pytest

import determined
from determined import workload
from tests.experiment import utils  # noqa: I100
from tests.experiment.fixtures import deepspeed_linear_model

deepspeed_config = {
    "train_batch_size": 16,
    "train_micro_batch_size_per_gpu": 4,
    "optimizer": {"type": "SGD", "params": {"lr": 0.001, "weight_decay": 3e-7}},
    "scheduler": {
        "type": "WarmupLR",
        "params": {"warmup_min_lr": 0, "warmup_max_lr": 0.001, "warmup_num_steps": 1000},
    },
    "gradient_clipping": 1.0,
    "prescale_gradients": False,
    "fp16": {
        "enabled": False,
    },
    "zero_optimization": {
        "stage": 0,
    },
}

# These environment variables are usually set by the launcher but we set them manually here
# since they are required by deepspeed.
os.environ["RANK"] = "0"
os.environ["LOCAL_RANK"] = "0"
os.environ["WORLD_SIZE"] = "1"
os.environ["MASTER_ADDR"] = "localhost"
os.environ["MASTER_PORT"] = "29500"


@pytest.mark.gpu
class TestDeepSpeedTrial:
    def setup_method(self) -> None:
        # This training setup is not guaranteed to converge in general,
        # but has been tested with this random seed.  If changing this
        # random seed, verify the initial conditions converge.
        self.trial_seed = 17
        self.hparams = {
            "global_batch_size": 16,
            "deepspeed_config": deepspeed_config,
            "test_manual_dataloader": False,
            "test_fail_dataset_repro_check": False,
            "test_manual_grad_acc": False,
            "test_fail_manual_grad_acc": False,
            "return_non_scalar_metrics": False,
            "test_custom_reducer": False,
        }
        self.data_parallel_only_auto_train_batch_calls = (
            deepspeed_config["train_batch_size"]
            // deepspeed_config["train_micro_batch_size_per_gpu"]
        )

    def test_linear_model(self) -> None:
        def make_workloads() -> workload.Stream:
            trainer = utils.TrainAndValidate()

            yield from trainer.send(
                steps=10,
                validation_freq=10,
                train_batch_calls=self.data_parallel_only_auto_train_batch_calls,
            )
            training_metrics, validation_metrics = trainer.result()

            for metrics in validation_metrics:
                assert "loss" in metrics

        controller = utils.make_trial_controller_from_trial_implementation(
            trial_class=deepspeed_linear_model.LinearDeepSpeedTrial,
            hparams=self.hparams,
            workloads=make_workloads(),
            trial_seed=self.trial_seed,
            expose_gpus=True,
        )
        controller.run()

    def test_manual_grad_acc_metrics(self) -> None:
        updated_hparams = copy.deepcopy(self.hparams)
        updated_hparams["test_manual_grad_acc"] = True

        def make_workloads() -> workload.Stream:
            trainer = utils.TrainAndValidate()

            yield from trainer.send(steps=10, validation_freq=10, train_batch_calls=1)
            training_metrics, validation_metrics = trainer.result()

            for metrics in validation_metrics:
                assert "loss" in metrics

        controller = utils.make_trial_controller_from_trial_implementation(
            trial_class=deepspeed_linear_model.LinearDeepSpeedTrial,
            hparams=updated_hparams,
            workloads=make_workloads(),
            trial_seed=self.trial_seed,
            expose_gpus=True,
        )
        controller.run()

    def test_fail_manual_grad_acc_metrics(self) -> None:
        updated_hparams = copy.deepcopy(self.hparams)
        updated_hparams["test_fail_manual_grad_acc"] = True

        def make_workloads() -> workload.Stream:
            trainer = utils.TrainAndValidate()

            yield from trainer.send(steps=10, validation_freq=10, train_batch_calls=1)
            training_metrics, validation_metrics = trainer.result()

            for metrics in validation_metrics:
                assert "loss" in metrics

        with pytest.raises(AssertionError):
            controller = utils.make_trial_controller_from_trial_implementation(
                trial_class=deepspeed_linear_model.LinearDeepSpeedTrial,
                hparams=updated_hparams,
                workloads=make_workloads(),
                trial_seed=self.trial_seed,
                expose_gpus=True,
            )
            controller.run()

    def test_custom_dataloader(self) -> None:
        updated_hparams = copy.deepcopy(self.hparams)
        updated_hparams["test_manual_dataloader"] = True

        def make_workloads() -> workload.Stream:
            trainer = utils.TrainAndValidate()

            yield from trainer.send(
                steps=10,
                validation_freq=10,
                train_batch_calls=self.data_parallel_only_auto_train_batch_calls,
            )
            training_metrics, validation_metrics = trainer.result()

            for metrics in validation_metrics:
                assert "loss" in metrics

        controller = utils.make_trial_controller_from_trial_implementation(
            trial_class=deepspeed_linear_model.LinearDeepSpeedTrial,
            hparams=updated_hparams,
            workloads=make_workloads(),
            trial_seed=self.trial_seed,
            expose_gpus=True,
        )
        controller.run()

    def test_fail_dataset_repro_check(self) -> None:
        updated_hparams = copy.deepcopy(self.hparams)
        updated_hparams["test_fail_dataset_repro_check"] = True

        def make_workloads() -> workload.Stream:
            trainer = utils.TrainAndValidate()

            yield from trainer.send(
                steps=10,
                validation_freq=10,
                train_batch_calls=self.data_parallel_only_auto_train_batch_calls,
            )
            training_metrics, validation_metrics = trainer.result()

            for metrics in validation_metrics:
                assert "loss" in metrics

        with pytest.raises(RuntimeError):
            controller = utils.make_trial_controller_from_trial_implementation(
                trial_class=deepspeed_linear_model.LinearDeepSpeedTrial,
                hparams=updated_hparams,
                workloads=make_workloads(),
                trial_seed=self.trial_seed,
                expose_gpus=True,
            )
            controller.run()

    def test_invalid_valid_dataset(self) -> None:
        def make_workloads() -> workload.Stream:
            trainer = utils.TrainAndValidate()

            yield from trainer.send(
                steps=10,
                validation_freq=10,
                train_batch_calls=self.data_parallel_only_auto_train_batch_calls,
            )

        with pytest.raises(determined.errors.InvalidExperimentException):
            _ = utils.make_trial_controller_from_trial_implementation(
                trial_class=deepspeed_linear_model.InvalidValidDatasetTrial,
                hparams=self.hparams,
                workloads=make_workloads(),
                trial_seed=self.trial_seed,
                expose_gpus=True,
            )

    def test_invalid_train_metric(self) -> None:
        def make_workloads() -> workload.Stream:
            trainer = utils.TrainAndValidate()

            yield from trainer.send(
                steps=10,
                validation_freq=10,
                train_batch_calls=self.data_parallel_only_auto_train_batch_calls,
            )

        with pytest.raises(determined.errors.InvalidExperimentException):
            controller = utils.make_trial_controller_from_trial_implementation(
                trial_class=deepspeed_linear_model.InvalidTrainMetricTrial,
                hparams=self.hparams,
                workloads=make_workloads(),
                trial_seed=self.trial_seed,
                expose_gpus=True,
            )
            controller.run()

    def test_invalid_valid_metric(self) -> None:
        def make_workloads() -> workload.Stream:
            trainer = utils.TrainAndValidate()

            yield from trainer.send(
                steps=10,
                validation_freq=10,
                train_batch_calls=self.data_parallel_only_auto_train_batch_calls,
            )

        with pytest.raises(determined.errors.InvalidExperimentException):
            controller = utils.make_trial_controller_from_trial_implementation(
                trial_class=deepspeed_linear_model.InvalidValidMetricTrial,
                hparams=self.hparams,
                workloads=make_workloads(),
                trial_seed=self.trial_seed,
                expose_gpus=True,
            )
            controller.run()

    def test_differing_valid_metric_keys(self) -> None:
        def make_workloads() -> workload.Stream:
            trainer = utils.TrainAndValidate()

            yield from trainer.send(
                steps=10,
                validation_freq=10,
                train_batch_calls=self.data_parallel_only_auto_train_batch_calls,
            )

        with pytest.raises(determined.errors.InvalidExperimentException):
            controller = utils.make_trial_controller_from_trial_implementation(
                trial_class=deepspeed_linear_model.DifferingValidMetricKeyTrial,
                hparams=self.hparams,
                workloads=make_workloads(),
                trial_seed=self.trial_seed,
                expose_gpus=True,
            )
            controller.run()

    def test_custom_reducer(self) -> None:
        updated_hparams = copy.deepcopy(self.hparams)
        updated_hparams["test_custom_reducer"] = True

        def make_workloads() -> workload.Stream:
            trainer = utils.TrainAndValidate()

            yield from trainer.send(
                steps=10,
                validation_freq=10,
                train_batch_calls=self.data_parallel_only_auto_train_batch_calls,
            )
            training_metrics, validation_metrics = trainer.result()

            for metrics in validation_metrics:
                assert "loss" in metrics

        controller = utils.make_trial_controller_from_trial_implementation(
            trial_class=deepspeed_linear_model.LinearDeepSpeedTrial,
            hparams=updated_hparams,
            workloads=make_workloads(),
            trial_seed=self.trial_seed,
            expose_gpus=True,
        )
        controller.run()

    def test_linear_non_scalar_metrics(self) -> None:
        updated_hparams = copy.deepcopy(self.hparams)
        updated_hparams["return_non_scalar_metrics"] = True

        def make_workloads() -> workload.Stream:
            trainer = utils.TrainAndValidate()

            yield from trainer.send(
                steps=10,
                validation_freq=10,
                train_batch_calls=self.data_parallel_only_auto_train_batch_calls,
            )
            training_metrics, validation_metrics = trainer.result()

            for metrics in validation_metrics:
                assert "loss" in metrics

        controller = utils.make_trial_controller_from_trial_implementation(
            trial_class=deepspeed_linear_model.LinearDeepSpeedTrial,
            hparams=updated_hparams,
            workloads=make_workloads(),
            trial_seed=self.trial_seed,
            expose_gpus=True,
        )
        controller.run()

    def test_linear_pipeline_model(self) -> None:
        def make_workloads() -> workload.Stream:
            trainer = utils.TrainAndValidate()

            yield from trainer.send(steps=1, validation_freq=1, train_batch_calls=1)
            training_metrics, validation_metrics = trainer.result()

            for metrics in validation_metrics:
                assert "loss" in metrics

        controller = utils.make_trial_controller_from_trial_implementation(
            trial_class=deepspeed_linear_model.LinearPipelineEngineTrial,
            hparams=self.hparams,
            workloads=make_workloads(),
            trial_seed=self.trial_seed,
            expose_gpus=True,
        )
        controller.run()

    def test_two_model_engines(self) -> None:
        def make_workloads() -> workload.Stream:
            trainer = utils.TrainAndValidate()

            yield from trainer.send(
                steps=1,
                validation_freq=1,
                train_batch_calls=self.data_parallel_only_auto_train_batch_calls,
            )
            training_metrics, validation_metrics = trainer.result()

            for metrics in validation_metrics:
                assert "loss1" in metrics
                assert "loss2" in metrics

        controller = utils.make_trial_controller_from_trial_implementation(
            trial_class=deepspeed_linear_model.LinearTwoEngineTrial,
            hparams=self.hparams,
            workloads=make_workloads(),
            trial_seed=self.trial_seed,
            expose_gpus=True,
        )
        controller.run()

    def test_checkpointing_and_restoring(self, tmp_path: pathlib.Path) -> None:
        def make_trial_controller_fn(
            workloads: workload.Stream,
            checkpoint_dir: Optional[str] = None,
            latest_checkpoint: Optional[Dict[str, Any]] = None,
            latest_batch: int = 0,
        ) -> determined.TrialController:
            return utils.make_trial_controller_from_trial_implementation(
                trial_class=deepspeed_linear_model.LinearPipelineEngineTrial,
                hparams=self.hparams,
                workloads=workloads,
                trial_seed=self.trial_seed,
                checkpoint_dir=checkpoint_dir,
                latest_checkpoint=latest_checkpoint,
                latest_batch=latest_batch,
                expose_gpus=True,
            )

        utils.checkpointing_and_restoring_test(make_trial_controller_fn, tmp_path)

    def test_restore_invalid_checkpoint(self, tmp_path: pathlib.Path) -> None:
        # Build, train, and save a checkpoint with the normal hyperparameters.
        checkpoint_dir = str(tmp_path.joinpath("checkpoint"))
        latest_checkpoint = None
        latest_batch = 0

        def make_workloads_1() -> workload.Stream:
            trainer = utils.TrainAndValidate()
            yield from trainer.send(
                steps=1,
                validation_freq=1,
                train_batch_calls=self.data_parallel_only_auto_train_batch_calls,
            )
            interceptor = workload.WorkloadResponseInterceptor()
            yield from interceptor.send(workload.checkpoint_workload())
            nonlocal latest_checkpoint, latest_batch
            latest_checkpoint = interceptor.metrics_result()["uuid"]
            latest_batch = trainer.get_latest_batch()

        controller1 = utils.make_trial_controller_from_trial_implementation(
            trial_class=deepspeed_linear_model.LinearDeepSpeedTrial,
            hparams=self.hparams,
            workloads=make_workloads_1(),
            trial_seed=self.trial_seed,
            checkpoint_dir=checkpoint_dir,
            expose_gpus=True,
        )
        controller1.run()

        # Verify that an invalid architecture fails to load from the checkpoint.
        def make_workloads_2() -> workload.Stream:
            trainer = utils.TrainAndValidate()
            yield from trainer.send(
                steps=1,
                validation_freq=1,
                train_batch_calls=self.data_parallel_only_auto_train_batch_calls,
            )

        with pytest.raises(AssertionError):
            controller2 = utils.make_trial_controller_from_trial_implementation(
                trial_class=deepspeed_linear_model.LinearTwoEngineTrial,
                hparams=self.hparams,
                workloads=make_workloads_2(),
                trial_seed=self.trial_seed,
                checkpoint_dir=checkpoint_dir,
                latest_checkpoint=latest_checkpoint,
                latest_batch=latest_batch,
                expose_gpus=True,
            )
            controller2.run()

    def test_reproducibility(self) -> None:
        def controller_fn(workloads: workload.Stream) -> determined.TrialController:
            return utils.make_trial_controller_from_trial_implementation(
                trial_class=deepspeed_linear_model.LinearPipelineEngineTrial,
                hparams=self.hparams,
                workloads=workloads,
                trial_seed=self.trial_seed,
                expose_gpus=True,
            )

        utils.reproducibility_test(controller_fn, steps=1000, validation_freq=100)

    def test_callbacks(self, tmp_path: pathlib.Path) -> None:
        checkpoint_dir = tmp_path.joinpath("checkpoint")
        latest_checkpoint = None
        latest_batch = 0

        controller = None

        def make_workloads1() -> workload.Stream:
            nonlocal controller

            yield workload.train_workload(1, 1, 0, 4), workload.ignore_workload_response
            assert controller is not None, "controller was never set!"
            assert controller.trial.counter.__dict__ == {
                "validation_steps_started": 0,
                "validation_steps_ended": 0,
                "checkpoints_ended": 0,
                "training_started_times": 1,
                "training_epochs_started": 2,
                "training_epochs_ended": 2,
            }

            yield workload.validation_workload(), workload.ignore_workload_response
            assert controller.trial.counter.__dict__ == {
                "validation_steps_started": 1,
                "validation_steps_ended": 1,
                "checkpoints_ended": 0,
                "training_started_times": 1,
                "training_epochs_started": 2,
                "training_epochs_ended": 2,
            }

            interceptor = workload.WorkloadResponseInterceptor()
            yield from interceptor.send(workload.checkpoint_workload())
            nonlocal latest_checkpoint, latest_batch
            latest_checkpoint = interceptor.metrics_result()["uuid"]
            latest_batch = 1
            assert controller.trial.counter.__dict__ == {
                "validation_steps_started": 1,
                "validation_steps_ended": 1,
                "checkpoints_ended": 1,
                "training_started_times": 1,
                "training_epochs_started": 2,
                "training_epochs_ended": 2,
            }

        hparams1 = dict(self.hparams)
        controller = utils.make_trial_controller_from_trial_implementation(
            trial_class=deepspeed_linear_model.LinearCallbackTrial,
            hparams=hparams1,
            workloads=make_workloads1(),
            checkpoint_dir=str(checkpoint_dir),
            expose_gpus=True,
        )
        controller.run()

        # Verify the checkpoint loading callback works.

        def make_workloads2() -> workload.Stream:
            yield workload.train_workload(1, 1, 0, 2), workload.ignore_workload_response

        controller = utils.make_trial_controller_from_trial_implementation(
            trial_class=deepspeed_linear_model.LinearCallbackTrial,
            hparams=self.hparams,
            workloads=make_workloads2(),
            checkpoint_dir=str(checkpoint_dir),
            latest_checkpoint=latest_checkpoint,
            latest_batch=latest_batch,
            expose_gpus=True,
        )
        controller.run()
        assert controller.trial.counter.__dict__ == {
            "validation_steps_started": 1,
            "validation_steps_ended": 1,
            "checkpoints_ended": 0,
            "training_started_times": 2,
            "training_epochs_started": 3,
            "training_epochs_ended": 3,
        }
