## Requirements

* Python 3.8+
* OpenCV (`opencv-python`, `opencv-contrib-python`)
* NumPy

Install dependencies:

```bash
pip install opencv-python opencv-contrib-python numpy
```

---

## Dataset Structure

Organize your dataset as follows:

```
faces/
│
├── Person1/
│   ├── image1.jpg
│   ├── image2.jpg
│   └── ...
├── Person2/
│   ├── image1.jpg
│   ├── image2.jpg
│   └── ...
└── ...
```

* Each folder name represents a **person’s name**.
* Images inside the folder are samples for that person.

---

## Usage

1. Place your dataset inside the `faces` folder as described above.
2. Run the training script:

```bash
python train_faces.py
```

