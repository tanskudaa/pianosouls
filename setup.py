import setuptools

setuptools.setup(
    name = "pianosouls-tanskudaa",
    version = "0.8",
    author = "Taneli Hongisto",
    author_email = "taneli.hongisto@tuni.fi",
    license = "GNU GPLv3",
    description = "MIDI notes and chords to virtual gamepad input",
    url = "https://github.com/tanskudaa/pianosouls",
    install_requires = ['pygame'],
    python_requires = '>= 3',
    entry_points = {
        'console_scripts': [
            'pianosouls=pianosouls:main'
        ]
    }
)