import glob
import numpy

from tables import *
from PIL import Image
import os

import warnings

from emotiw.caglar.bbox import BoundingBox

"""
Convert the images to grayscale.
"""
def get_grayscale(path):
    img = Image.open(path)
    img.draft("L", img.size)
    img = img.convert("L")
    return img

"""
Resize the image given img and newsize.
"""
def resize_image(img, newsize, mode=None):
    return img.resize(newsize)

"""
Get the images from the path.
"""
def get_images(path, batches):
    rval = {}
    for batch in batches:
        list = glob.glob("{}{}/*.png".format(path, batch))
        rval[batch] = list
    return rval

"""
Get the scaled bounding boxes.
"""
def get_scaled_bbox(bbox, orig_size, scaled_size):
    x_scale_ratio = float(scaled_size[0]) / float(orig_size[0])
    y_scale_ratio = float(scaled_size[1]) / float(orig_size[1])
    bbox[2] = int(bbox[2] * y_scale_ratio)
    bbox[3] = int(bbox[3] * x_scale_ratio)
    bbox[4] = int(bbox[4] * y_scale_ratio)
    bbox[5] = int(bbox[5] * x_scale_ratio)
    return bbox

"""
Get the bounding boxes.
"""
def get_bounding_boxes(path, batches, limit=None):
    rval = {}
    count = 0
    for batch in batches:
        list = glob.glob("{}{}/*.txt".format(path, batch))
        batch_holder = {}
        if limit is not None:
            if count >= limit:
                break
        for item in list:
            name = int(item.split('/')[-1].rstrip('.txt').split('-')[-1])
            val = numpy.loadtxt(item, delimiter=',', skiprows=1)
            if val.ndim == 1:
                val = val.reshape((1,6))
            batch_holder[name] = val.tolist()
            count += 1
        rval[batch] = batch_holder
    return rval, count

"""
Process the image data.
"""
def save_img_data(img_path=None,
        bbox_path=None,
        save_path=None,
        h5_name=None,
        limit=None,
        optimized=True,
        batchsize=100,
        newsize=None):

    if newsize is None:
        newsize = [256, 256]

    assert img_path is not None
    assert bbox_path is not None
    assert save_path is not None

    bbox_dirs = os.walk(bbox_path).next()[1]
    img_dirs = os.walk(bbox_path).next()[1]

    if h5_name is None:
        h5_name = "face_data.h5"
    else:
        assert h5_name.endswith(".h5")

    filename = os.path.join(save_path, h5_name)

    if not optimized:
        complevel = 2
    else:
        complevel = 1

    h5file = openFile(filename, mode = "w", title = "Face bounding boxes data.")
    gcolumns = h5file.createGroup(h5file.root, "Data", title="Face Data")

    filters = Filters(complib='blosc', complevel=complevel)

    table = h5file.createTable(gcolumns, 'bboxes', BoundingBox, "Bounding boxes", filters=filters)

    print "Loading bounding boxes..."
    bboxes, nbboxes = get_bounding_boxes(bbox_path, bbox_dirs, limit=limit)
    print "Bounding boxes are loaded."

    tbl_bboxes = table.row
    images_atom = Float32Atom(shape=())

    images = h5file.createCArray(gcolumns,
                "X",
                atom=images_atom,
                shape=[nbboxes, numpy.prod(newsize)],
                title="image pixels", filters=filters)

    i = 0
    print "Started saving the h5 file."

    files_in_bucket = 0
    faces_in_bucket = []
    for (key, bbox) in bboxes.iteritems():
        for (name, val) in bbox.iteritems():
            face_path = "{}/{}/{}.png".format(img_path, key, name)

            if optimized:
                face_img = get_grayscale(face_path)
            else:
                if os.access(face_path, os.R_OK):
                    face_img = get_grayscale(face_path)
                else:
                    warnings.warn("%s is dead!" % face_path)
                    continue

            #Warning PIL returns the size as: h, v or x*y not as row and columns.
            orig_size = face_img.size
            face_no = 0
            tbl_bboxes = table.row

            if files_in_bucket == batchsize:
                table.flush()
                images[i-batchsize:i] = faces_in_bucket
                #Empty the buckets
                files_in_bucket = 0
                faces_in_bucket = []

            resized_face = resize_image(face_img, newsize)
            faces_in_bucket.append(numpy.array(resized_face.getdata()))

            for j in xrange(len(val)):
                resized_bbox = get_scaled_bbox(val[j], orig_size, newsize)
                tbl_bboxes["picasaBatchNumber"] = int(resized_bbox[0])
                tbl_bboxes["idxInPicasaBatch"] = int(resized_bbox[1])
                tbl_bboxes["faceno"] = face_no
                tbl_bboxes["imgno"] = i
                tbl_bboxes["row"] = resized_bbox[2]
                tbl_bboxes["col"] = resized_bbox[3]
                tbl_bboxes["height"] = resized_bbox[4]
                tbl_bboxes["width"] = resized_bbox[5]
                tbl_bboxes.append()
                face_no +=1

            i += 1
            files_in_bucket += 1

    print "There are %d images in the dataset." %(i)

    if files_in_bucket !=0:
        table.flush()
        images[i-len(faces_in_bucket):i] = faces_in_bucket


    indexrows = table.cols.imgno.createIndex()
    print "Saving %s has been completed." % h5_name
    h5file.close()
