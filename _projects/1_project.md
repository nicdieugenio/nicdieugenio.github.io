---
layout: page
title: project 1
description: with background image
img: assets/img/cluster.png
importance: 1
category: work
related_publications: true
---


## How Does Cluster Expansion Work?

The mathematical proof for the **cluster expansion method** is complex and lengthy. However, its motivation is pretty straightforward and fun to play with.

## From the Ising Model to the Cluster Expansion

The simplest way to understand cluster expansion is to start from a generalized **Ising model** for a magnetic material. The atoms are here disposed on a square lattice where the spins have the values \(+1\) (spin up) or \(-1\) (spin down), as in Fig. \(\ref{ising}\).

![Ising model square lattice](assets/img/ising.png)

Now, one can write the Hamiltonian for such system in terms of the spin \(s\) of each lattice site, as:

\[
H(s) = C + \sum_{\langle i j \rangle}J_{ij}s_{i}s_{j} - \mu\sum_{j}^{N}h_{j}s_{j}
\]

where \(C\) is a scaling factor, \(J_{ij}\) the interaction coefficient between sites \(i,j\), \(N\) is the number of occupied lattice sites, \(\mu\) the magnetic moment and \(h\) the interaction with a given external magnetic field. Here, the notation \(\langle ij \rangle\) employed indicates that the summation is performed all nearest neighbors pairs.

The greatness of the Ising model is hidden in the fact that one can now use the same formalism to describe a binary alloy: instead of representing the spins, now the value \(-1\) indicates the presence of an element A and \(+1\) the presence of an element B! The Hamiltonian can thus be rewritten as:

\[
H(\sigma) = J_{0} + J_{1}\sum_{j}^{N}\sigma_{j} + J_{2}\sum_{\langle i j \rangle}J_{ij}\sigma_{i}\sigma_{j} 
\]

where \(\sigma\) represents the given configuration (atom A or B) found at each lattice site.

Of course, the energy of a binary alloy cannot be computed by just considering the contributions coming from nearest neighbors pairs and individual atoms: the Hamiltonian has to be expanded in order to consider contributions of groups of atoms (next nearest neighbors, triplets etc.), like in Fig. \(\ref{cluster}\).

![Example of cluster selection](assets/img/cluster.png)

Another error would be, on the opposite, to consider all possible groups: it is not practical as it would be too heavy to compute! It is smarter to include only clusters that provide a good level of *accuracy*. 

At this point, the Ising Hamiltonian can be expanded to include such clusters, thus obtaining the standard form of the **Cluster Expansion equation**, as:

\[
H(\sigma) = \sum_{\text{clusters } f} J_{f} \Pi(\sigma)_{f}
\]

Written in this way, \(\Pi(\sigma)\) represents the normalized spin product of a given cluster over the total lattice.
```
