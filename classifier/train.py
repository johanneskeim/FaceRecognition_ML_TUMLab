from time import perf_counter

import torch
from data.data_loaders import get_data_loaders
from data.web_face_dataset import WebfaceDataset
from joblib import dump
from models.inception_resnet_v1 import InceptionResnetV1
from sklearn.neighbors import RadiusNeighborsClassifier
from utils.vis_utils import extract_embeddings


def get_data():
    print("getting data...")
    timing = perf_counter()

    CLASSES_PER_BATCH = 30
    SAMPLES_PER_CLASS = 40

    dataset = WebfaceDataset("../../data/Aligned_CASIA_WebFace")
    # dataset = WebfaceDataset("datasets/CASIA-WebFace")

    train_loader, _, _ = get_data_loaders(
        dataset,
        CLASSES_PER_BATCH,
        SAMPLES_PER_CLASS,
        train_proportion=0.8,
        val_proportion=0.1,
        test_proportion=0.1,
    )

    if torch.cuda.is_available():
        checkpoint = torch.load(
            "checkpoints/young-leaf-128_epoch_19", map_location=torch.device("cuda")
        )
    else:
        checkpoint = torch.load(
            "checkpoints/young-leaf-128_epoch_19", map_location=torch.device("cpu")
        )
    model = InceptionResnetV1()
    model.load_state_dict(checkpoint["model_state_dict"])

    if torch.cuda.is_available():
        model = model.cuda()

    embeddings, targets = extract_embeddings(train_loader, model)

    print(f"took {perf_counter() - timing}")

    return embeddings[:10], targets[:10]


def train_classifier(embeddings, targets):
    print("training classifier...")
    timing = perf_counter()

    classifier = RadiusNeighborsClassifier(radius=1, outlier_label=-1, n_jobs=-1)
    print("initialized model")
    classifier.fit(embeddings, targets)
    print(f"took {perf_counter() - timing}")

    return classifier


def save_classifier(classifier):
    print("saving...")
    dump(classifier, "face_recognition_classifier.joblib")
    print("done")


if __name__ == "__main__":
    torch.manual_seed(42)

    embeddings, targets = get_data()
    classifier = train_classifier(embeddings, targets)
    save_classifier(classifier)