import setuptools

try:
    with open("README.md", "r", encoding="utf-8") as fh:
        long_description = fh.read()
except FileNotFoundError:
    long_description = 'Not provided'

setuptools.setup(
    name="jire",
    version="0.0.1",
    author="Christian Lölkes",
    author_email="christian.loelkes@gmail.com",
    description="Jitsi reservation system",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/loelkes/jire",
    packages=setuptools.find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Framework :: Flask",
        "Programming Language :: Python :: 3.6",
        "Topic :: Communications :: Conferencing",
    ],
    python_requires='>=3.6',
    install_requires=[
          'Flask',
          'Flask-Bootstrap4',
          'python-dotenv',
          'Flask-API',
          'Flask-WTF',
          'WTForms==3.0.0a1',
          'python-dateutil',
          'pytz',
    ],
)
