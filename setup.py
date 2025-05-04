import setuptools


def get_requirements(file_name):
    with open(file_name) as f:
        return f.read().splitlines()


setuptools.setup(
    name="alisa_blind_chess",
    version="0.1.0",
    description="Alice Skill - Blind Chess",
    author_email="S0finma@ya.ru",  # change 0 to o
    install_requires=get_requirements("requirements.txt"),
    packages=setuptools.find_packages(),
    include_package_data=True,
    package_data={
        '': ['*.py', '*.txt', '*.md'],
    },
)
