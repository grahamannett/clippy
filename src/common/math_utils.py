import numpy as np

# These are similar to basic sklearn functions but I am avoiding sklearn if possible


def row_norms(x: np.ndarray, squared: bool = False) -> np.ndarray:
    """
    equivalent to sklearn.utils.extmath.row_norms
    """
    norms = np.einsum("ij,ij->i", x, x)
    if not squared:
        norms = np.sqrt(norms)
    return norms


def normalize(x):
    """
    equivalent to sklearn.preprocessing.normalize
    """
    norms = row_norms(x)

    return x / norms[:, np.newaxis]


def cosine_similarity(x: np.ndarray, y: np.ndarray, to_norm: bool = True) -> np.ndarray:
    """
    equivalent to sklearn.metrics.pairwise.cosine_similarity

    Args:
        x (np.ndarray): n array
        y (np.ndarray): n x m array
        normalize (bool, optional): _description_. Defaults to True.

    Returns:
        _type_: _description_
    """
    if x.ndim == 1:
        x = x[np.newaxis, :]

    if to_norm:
        x = normalize(x)
        y = normalize(y)

    return x @ y.T
