from pathlib import Path
from time import perf_counter

import torch
import wandb
from tqdm import tqdm

from data.data_loaders import get_data_loaders
from data.web_face_dataset import WebfaceDataset
from models.inception_resnet_v1 import InceptionResnetV1
from training import triplet_generator
from training.loss_function import OnlineTripletLoss
from utils.vis_utils import plot_embeddings


def train(model, train_loader, val_loader, loss_function, optimizer, epochs):
    for epoch in range(epochs):
        print(f"epoch {epoch + 1} of {epochs}")

        embeddings, targets = train_epoch(model, train_loader, loss_function, optimizer)

        evaluate(model, val_loader)

        save_checkpoint(model, optimizer, epoch)

        embedding_visualization_timing = perf_counter()
        fig = plot_embeddings(embeddings, targets)
        fig.show()
        wandb.log(
            {
                "embedding_plot": fig,
                "embedding_visualization_timing": (
                    perf_counter() - embedding_visualization_timing
                ),
            }
        )


def train_epoch(model, train_loader, loss_function, optimizer):

    total_loss = 0
    model_forward_timing = 0
    loss_timing = 0
    loss_backward_timing = 0
    optimizer_step_timing = 0
    model.train()
    losses = []

    for batch_idx, (data, target) in tqdm(
        enumerate(train_loader), total=len(train_loader), desc="processing batch: "
    ):
        target = target if len(target) > 0 else None

        if not type(data) in (tuple, list):
            data = (data,)

        if torch.cuda.is_available():
            data = tuple(d.cuda() for d in data)
            if target is not None:
                target = target.cuda()

        optimizer.zero_grad()

        timing = perf_counter()
        outputs = model(*data)
        model_forward_timing += perf_counter() - timing

        if type(outputs) not in (tuple, list):
            outputs = (outputs,)

        loss_inputs = outputs

        if target is not None:
            target = (target,)
            loss_inputs += target
        timing = perf_counter()
        loss_outputs = loss_function(*loss_inputs)
        loss_timing += perf_counter() - timing

        if loss_outputs is None:
            continue

        loss = loss_outputs[0] if type(loss_outputs) in (tuple, list) else loss_outputs
        losses.append(loss.item())
        total_loss += loss.item()
        timing = perf_counter()
        loss.backward()
        loss_backward_timing += perf_counter() - timing

        timing = perf_counter()
        optimizer.step()
        optimizer_step_timing += perf_counter() - timing

        if batch_idx % 10 == 0:  # 10
            wandb.log(
                {
                    "training_loss": total_loss / (batch_idx + 1),
                    "model_forward_timing": model_forward_timing / (batch_idx + 1),
                    "loss_timing": loss_timing / (batch_idx + 1),
                    "loss_backward_timing": loss_backward_timing / (batch_idx + 1),
                    "optimizer_step_timing": optimizer_step_timing / (batch_idx + 1),
                }
            )

    return (
        outputs[0].detach(),
        target[0],
    )  # return final batch embeddings for visualization


def evaluate(model, val_loader):
    pass


def save_checkpoint(model, optimizer, epoch_num):
    checkpoint_folder = Path("checkpoints/")
    checkpoint_folder.mkdir(parents=True, exist_ok=True)
    checkpoint_file = checkpoint_folder / (wandb.run.name + f"_epoch_{epoch_num}")
    torch.save(
        {
            "epoch": epoch_num,
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "run_name": wandb.run.name,
        },
        checkpoint_file,
    )
    wandb.save(str(checkpoint_file))


if __name__ == "__main__":
    torch.manual_seed(42)

    EPOCHS = 10
    LEARNING_RATE = 0.01
    DROPOUT_PROB = 0.6
    SCALE_INCEPTION_A = 0.17
    SCALE_INCEPTION_B = 0.10
    SCALE_INCEPTION_C = 0.20
    MARGIN = 1

    CLASSES_PER_BATCH = 30
    SAMPLES_PER_CLASS = 40
    BATCH_SIZE = CLASSES_PER_BATCH * SAMPLES_PER_CLASS

    wandb.init(
        project="face-recognition",
        entity="application-challenges-ml-lab",
        # mode="disabled",
        config={
            "epochs": EPOCHS,
            "batch_size": BATCH_SIZE,
            "classes_per_batch": CLASSES_PER_BATCH,
            "samples_per_class": SAMPLES_PER_CLASS,
            "learning_rate": LEARNING_RATE,
            "dropout_prob": DROPOUT_PROB,
            "scale_inception_a": SCALE_INCEPTION_A,
            "scale_inception_b": SCALE_INCEPTION_B,
            "scale_inception_c": SCALE_INCEPTION_C,
        },
    )

    model = InceptionResnetV1(
        DROPOUT_PROB, SCALE_INCEPTION_A, SCALE_INCEPTION_B, SCALE_INCEPTION_C
    )
    if torch.cuda.is_available():
        model = model.cuda()

    wandb.watch(model)

    # dataset = WebfaceDataset("../../data/Aligned_CASIA_WebFace")
    dataset = WebfaceDataset("datasets/CASIA-WebFace")

    train_loader, val_loader, _ = get_data_loaders(
        dataset,
        CLASSES_PER_BATCH,
        SAMPLES_PER_CLASS,
        train_proportion=0.01,
        val_proportion=0.89,
        test_proportion=0.1,
    )

    optimizer = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)
    triplet_loss = OnlineTripletLoss(MARGIN, triplet_generator.get_semihard)
    train(model, train_loader, val_loader, triplet_loss, optimizer, epochs=EPOCHS)
