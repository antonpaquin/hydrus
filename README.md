## Hydrus + Neural Network

The Illustration2Vec network can automatically assign tags to images. This repo is an attempt to integrate that into hydrus.

To run, first you should be able to run hydrus from source.

Then you should download the tagging neural network --
https://github.com/antonpaquin/hydrus/releases/tag/illust2vec
contained in this release.
(This is currently built for linux -- I doubt it will work on windows, but not sure).

- Untar the archive anywhere
- **back up your damn databases this is experimental and likely to break**
- Run hydrus
- Select some images
- Right click -> open selection from automatic tagging
- Under "load model", select the illust2vec **directory** contained in the archive
  - (this contains the model and all dependencies for Python 2.7.14 on Arch Linux)
- Set threshold and batch size
  - threshold 0.5 works pretty okay
  - batch size can be whatever but higher (10 to 100) might speed up classifying larger sets of images
- Hit "run tagging"
  - Hydrus will freeze because I don't know the internals well enough yet
- After a while hit "accept all"
  - "accept selected" does nothing at this point
- Go check your tags they should have whatever tags illust2vec thinks is appropriate
  - Everything is 1girl
  - Every girl is a touhou character
  - Hair color seems to be random

Models for other OSes can be generated by translating this process:
- Copy "tag.py", "tag_list.json", and "illust2vec.h5" to a new directory (let's call it "dest")
- Install the requirements to the destination directory
  - cd dest
  - pip2 install -t . keras tensorflow opencv-python
  
Thanks to this system models can be distributed completely separately from the main hydrus program
