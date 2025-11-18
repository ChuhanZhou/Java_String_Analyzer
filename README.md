# Java Static Analyzer

This repository contains the implementation of Java syntactic analysis and semantic analysis. This analyzer is designed to handle integers, booleans and extends to strings in Java programs, implementing static analysis of string operations through novel abstractions.

## Setup

### Step 0: Clone git
```bash
git clone https://github.com/ChuhanZhou/Java_Static_Analyzer.git
```

### Step 1: Clone [JPAMB](https://github.com/kalhauge/jpamb) benchmark suite

#### Linux and macOS:
```bash
cd Java_Static_Analyzer
sh clone_jpamb.sh
```

#### Windows:
```bash
cd Java_Static_Analyzer
clone_jpamb.sh
```

### Step 2: Install environment

#### pip

* Python 3.13+

```bash
pip install -r requirements.txt
```

#### conda

```bash
conda env create -f environment.yml
conda activate env_jsa
```