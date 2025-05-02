import os

# demo recurse filesystem

# create 2 flat dictionaries for
# forward and reverse search
# path->handle and handle->path

# create dictionary for directory content

# global handle incremented
next_handle=0
path2handle={}
handle2path={}
dir2handle={}

# example
# path2handle = {"/lib":{0:5,"file1":10,"file2":11}} TODO
# handle2path = {5:"/lib", 10:"/lib/file1", 11:"/lib/file2}

DIR=const(16384)
#FILE=const(32768)

# for given handle find it's parent
# actually a handle of directory which
# holds this file
def parent(handle):
  path=handle2path[handle]
  if path[-1]=="/" and path!="/":
    dirname=path[:path[:-1].rfind("/")+1]
  else:
    dirname=path[:path.rfind("/")+1]
  return path2handle[dirname][0]

# path: full path string
# recurse: number of subdirectorys to recurse into
def ls(path,recurse):
  global next_handle
  try:
    dir=os.ilistdir(path)
  except:
    return
  # if path doesn't trail with slash, add slash
  if path[-1]!="/":
    path+="/"
  # path -> handle and handle -> path
  # "/lib" in {}
  if path in path2handle:
    current_dir=path2handle[path][0]
  else:
    current_dir=next_handle
    next_handle+=1
    path2handle[path]={0:current_dir}
    handle2path[current_dir]=path
  # id -> directory list
  if not current_dir in dir2handle:
    dir2handle[current_dir]={}
  for obj in dir:
    objname=obj[0]
    fullpath=path+objname
    if objname in path2handle[path]:
      current_handle=path2handle[path][objname]
    else:
      current_handle=next_handle
      next_handle+=1
    if obj[1]==16384: # obj[1]==DIR
      print(path,"DIR:",obj)
      if recurse>0:
        dir2handle[current_dir][ls(fullpath,recurse-1)]=obj
    else: # obj[1]==FILE
      dir2handle[current_dir][current_handle]=obj
      print(path,"FILE:",obj)
      if not objname in path2handle[path]:
        path2handle[path][objname]=current_handle
        handle2path[current_handle]=fullpath
  return current_dir

ls("/",1)
print(handle2path)
print(path2handle)
print(dir2handle)
# listing again should not change or add anything
#ls("/",3) # FIXME
#print(handle2path)
#print(path2handle)
#print(dir2handle)
