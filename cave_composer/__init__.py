"""Controllable cave worlds; no Blender import required for geometry generation."""
__version__ = "0.2.0"


def generate(config, seed=42, output=None, **kwargs):
    from .pipeline import generate as generate_scene
    return generate_scene(config, seed, output, **kwargs)


def sample(split="train", difficulty="medium", seed=42, output=None, **kwargs):
    from .dataset import sample_config, scene_seed
    split=split.lower()
    return generate(sample_config(split, difficulty, seed), scene_seed(split,seed), output, **kwargs)
