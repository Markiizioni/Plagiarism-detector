this folder contains code that can be used by alternative flask
implementations, for example quart. the code therefore cannot do any
io, nor be part of a likely io path. finally this code cannot use the
flask globals.