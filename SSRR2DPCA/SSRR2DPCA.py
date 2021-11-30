"""Structured sparsity regularized robust 2D principal component analysis."""

# Authors: Shion Matsumoto   <matsumos@umich.edu>
#          Rohan Sinha Varma <rsvarma@umich.edu>
#          Marcus Koenig     <marcusko@umich.edu>
#          Yaning Zhang      <yaningzh@umich.edu>

import numpy as np
import spams
from scipy import linalg
from scipy.linalg import eig, svd, svdvals
from sklearn.preprocessing import MinMaxScaler


def iterBDD(X, E, U, V, r, c, tol, max_iter):
    """Iterative bi-directional decomposition.

    Step 1 of the two-stage alternating minimization algorithm for the
    solution to the optimization problem of structured sparsity regularized
    robust 2D-PCA.

    Parameters
    ----------
    X : array, shape (n_samples, m, n)
        Data

    E : array, shape (n_samples, m, n)
        Structured sparse matrices. If none provided, set to E = 0_(m, n) as stated by Sun et al. (2015)

    U : array, shape(U)
        Initial left projection matrix. If none provided, set to U = [ I_(r,r) | 0_(r,m-r) ] as stated
        by Sun et al. (2015)

    V : array, shape(V)
        Initial right projection matrix. If none provided, set to V = [ I_(c,c) | 0_(c,n-c) ] as stated
        by Sun et al. (2015)

    r : int
        Row dimensionality reduction

    c : int
        Column dimensionality reduction

    tol : float
        Tolerance criterion for convergence

    max_iter : int
        Maximum number of iterations

    Returns
    -------
    U : array, shape (m, r)
        Final left projection matrix

    V : array, shape (n, c)
        Final right projection matrix
    """
    ii = 0
    while ii < max_iter and ~has_converged():
        # Eigendecomposition of Cv
        VVT = V.dot(V.T)
        XE = X - E
        Cv = np.einsum("ij,lkj->lik", VVT, XE)
        Cv = np.mean(np.einsum("ijk,mkl->mil", XE, Cv), axis=0)
        wu, _ = eig(Cv, left=True)

        # Eigendecomposition of Cu
        Cu = np.mean((X - E) @ U @ U.T @ (X - E).T, axis=2)
        wv, _ = eig(Cu, left=True)

        # Update U and V
        U = wu[:, :r]
        V = wv[:, :c]

        # Update iteration
        ii += 1

    return U, V


def feature_outlier_extractor(X, U, V, E, tol, max_iter):
    """Feature matrix and structured outlier extraction.

    Step 2 of the two-stage alternating minimization algorithm for the
    solution to the optimization problem of structured sparsity
    regularized robust 2D-PCA.

    Parameters
    ----------
    X : array, shape (n_samples, m, n)
        Data

    E : array, shape (n_samples, m, n)
        Structured sparse matrices

    U : array, shape (r, r)
        Initial left projection matrix

    V : array, shape (c, c)
        Initial right projection matrix

    tol : float
        Tolerance criterion for convergence

    Returns
    -------
    S : array, shape (n_samples, m, n)
        Feature matrix

    E : array, shape (n_samples, m, n)
        Structured sparse outliers matrix
    """
    m, n = E.shape()
    ii = 0
    while ii < max_iter and ~hasConvered():
        # Bi-directional projection
        S = U.T.dot((X - E).dot(V))

        # Proximal gradient method to solve structured sparsity regularized problem
        O = np.array([1])  # 3x3 neighboring grids
        for i, s in enumerate(S):
            e = spams.proximalFlat(X - U.dot(s.dot(V.T)), regul="elastic-net")
            E[i] = e.reshape((m, n))

        # Update iteration
        ii += 1

    return S, E


def has_converged():
    """Determine convergence

    Parameters
    ----------

    Returns
    -------
    has_converged : bool
        True if converged, False otherwise
    """
    return False


def ssrr2dpca(X, scale):
    """Structured sparsity regularized robust 2D principal component
    analysis (SSR-R2D-PCA).
    """
    X = X.astype(float)

    # Get dimensions of data (following notations of paper)
    T, m, n = np.shape(X)

    # # Scale values to lie within [0,1]
    # X_scaled = MinMaxScaler().fit_transform(X, )

    # Center data
    X -= X.mean(axis=0)

    # Calculate dimension reduction parameters
    r = m / scale
    c = n / scale

    # Initialize projection and structured sparse matrices
    U = np.vstack((np.eye(r, r), np.zeros((m - r, r))))  # shape(U) = (m,r)
    V = np.vstack((np.eye(c, c), np.zeros((n - c, c))))  # shape(V) = (n,c)
    E = np.tile((np.zeros((1, m, n))), (T, 1, 1))

    # Get left and right projection matrices
    l = 1 / np.sqrt(m * n)
    U, V = iterBDD(X, E, U, V, r, c)

    # Get feature matrix and structured outliers
    S, E = feature_outlier_extractor(X, U, V, tol=1e-3)

    return U, V, S, E


class SSRR2DPCA:
    """Structured sparsity regularized robust 2D principal component
    analysis (SSR-R2D-PCA).

    Dimensionality reduction technique based on the algorithm detailed in
    "Robust 2D principal component analysis: A structured sparsity regularized
    approach" by Yipeng Sun, Xiaoming Tao, Yang Li, and Jianhua Lu.

    The construction of this class is based on scikit-learn's PCA class.

    Parameters
    ----------
    n_components : int
        Number of principal components

    l : float
        Sparsity regularization term

    b : array, shape (n_components)
        Structured sparsity regularization term, default value of l when w=1

    U : array, shape (nx, ny, n_components)
        Left projection matrices

    V : array, shape (nx, ny, n_components)
        Right projection matrices

    E : array, shape (nx, ny, n_samples)
        Structured outliers

    Attributes
    ----------
    components_ : array, shape (n_components, n_features)
        Principal components

    explained_variance_ : array, shape (n_components,)
        Amount of variance explained by each of the principal components

    explained_variance_ratio_ : array, shape (n_components,)
        Ratio (percentage) of variance explained by each of the principal
        components

    singular_values_ : array, shape (n_components,)
        Singular values associated with each principal component

    mean_ : array, shape (nx, ny)
        Empiricial mean estimated from training data

    n_components_ : int
        Number of principal components

    n_feautres_ : array, shape (2,)
        Number of features in x- and y-directions

    n_samples_ : int
        Number of samples in the training data

    References
    ----------
    Yipeng Sun et al. “Robust 2D principal component analysis:
    A structured sparsity regularized approach”.
    In:IEEE Transactions on Image Processing 24.8 (Aug. 2015), pp. 2515–2526.
    ISSN:10577149.DOI:10.1109/TIP.2015.2419075.
    """

    def __init__(self, r=None, c=None, lam=None, beta=None):
        self.r_ = r
        self.c_ = c
        self.lam_ = lam
        self.beta_ = beta
        self.U_ = None
        self.V_ = None
        self.S_ = None
        self.E_ = None

    def fit(self, X):
        """Fit model with data X.

        Parameters
        ----------
        X : array, shape (n_samples, n_features_x, n_features_y)
            Training data used to fit model

        Returns
        -------
        self : object
            Returns object instance
        """
        X = X.astype(float)

        # Get dimensions of data (following notations of paper)
        T, m, n = np.shape(X)
        r, c = self.n_components_x_, self.n_components_y_
        self.n_samples_, self.n_features_y_, self.n_features_x_ = T, m, n

        # # Scale values to lie within [0,1]
        # X_scaled = MinMaxScaler().fit_transform(X, )

        # Center data
        self.mean_ = np.mean(X, axis=0)
        X -= self.mean_

        # Initialize projection and structured sparse matrices
        U = np.vstack((np.eye(r, r), np.zeros((m - r, r))))  # shape(U) = (m,r)
        V = np.vstack((np.eye(c, c), np.zeros((n - c, c))))  # shape(V) = (n,c)
        E = np.tile((np.zeros((1, m, n))), (T, 1, 1))

        # Get left and right projection matrices
        self.U, self.V = iterBDD(X, E, U, V)

        # Get feature matrix and structured outliers
        self.S, self.E = feature_outlier_extractor(X, self.U, self.V, tol=1e-3)

        return self

    def transform(self, X):
        """Apply dimensionality reduction to X.

        Parameters
        ----------
        X : array, shape (n_samples, n_features)
            Data

        Returns
        -------
        X_transformed : shape (n_samples, n_components)
            X transformed
        """
        return 0

    def fit_transform(self, X):
        """Fit model with data X and apply dimensionality reduction to X.

        Parameters
        ----------
        X : array, shape (n_samples, n_features)
            Training data used to fit model

        Returns
        -------
        X_transformed : array (n_samples, n_components)
            X transformed using dimensionality reduction
        """
        self.fit(X)
        self.transform(X)

        return 0
