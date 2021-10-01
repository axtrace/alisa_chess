import setuptools


def get_requirements(file_name):
    with open(file_name) as f:
        return f.read().splitlines()


setuptools.setup(
    name="alice_blind_chess",
    version="0.1.0",
    description="Alice Skill - Blind Chess",
    author_email="Sofinma@ya.ru",
    install_requires=get_requirements("requirements.txt"),
    packages=setuptools.find_packages(),
)
