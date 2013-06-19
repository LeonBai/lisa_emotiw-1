# Copyright (c) 2013 University of Montreal, Pascal Vincent
# Pierre-Luc Carrier, Vincent Archambault, Pascal Lamblin
#
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * The names of the authors and contributors to this software may not be
#       used to endorse or promote products derived from this software without
#       specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS ''AS IS'' AND ANY
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDERS BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import pdb

import os
import sys
import cv
import Image
import ImageDraw
import ImageFont
import numpy
import sys
import csv
from scipy import io as sio

from emotiw.common.utils.pathutils import locate_data_path, search_replace

#sys.path.append(os.getcwd()+"/../../../vincentp")
#from preprocess_face import * # getEyesPositions,getFaceBoundingBox

basic_7emotion_names = ["anger", "disgust", "fear", "happy", "sad", "surprise", "neutral"]
keypoints_names = ['left_eyebrow_inner_end', 'bottom_lip_top_left_midpoint', 'right_ear_top', 'mouth_bottom_lip_top', 'face_left', 'left_eyebrow_outer_midpoint', 'left_jaw_1', 'left_jaw_0', 'bottom_lip_top_left_center', 'left_eyebrow_center_top', 'left_eye_outer_corner', 'top_lip_bottom_right_midpoint', 'mouth_bottom_lip', 'left_mouth_outer_corner', 'left_eyebrow_center_bottom', 'top_lip_bottom_left_center', 'right_eyebrow_inner_end', 'chin_center', 'right_eyebrow_outer_midpoint', 'left_ear_bottom', 'right_eye_outer_corner', 'left_eyebrow_outer_end', 'top_lip_bottom_left_midpoint', 'bottom_lip_bottom_right_midpoint', 'right_eye_center_top', 'right_nostril_inner_end', 'top_lip_bottom_center', 'face_center', 'right_eye_inner_corner', 'right_eyebrow_center_top', 'left_eyebrow_center', 'right_ear_bottom', 'mouth_left_corner', 'nostrils_center', 'right_eyebrow_inner_midpoint', 'mouth_right_corner', 'chin_center_top', 'nose_ridge_bottom', 'right_eye_center', 'left_eye_bottom_outer_midpoint', 'left_eye_pupil', 'right_jaw_2', 'right_jaw_1', 'right_jaw_0', 'top_lip_bottom_right_center', 'top_lip_top_right_center', 'left_nostril_inner_end', 'right_eyebrow_center_bottom', 'chin_right', 'mouth_top_lip_bottom', 'right_ear_canal', 'bottom_lip_bottom_center', 'mouth_top_lip', 'right_eyebrow_center', 'chin_left', 'left_eye_top_outer_midpoint', 'left_jaw_2', 'nose_tip', 'bottom_lip_bottom_left_center', 'left_eye_top_inner_midpoint', 'right_eye_top_outer_midpoint', 'left_eye_bottom_inner_midpoint', 'top_lip_top_left_center', 'bottom_lip_bottom_right_center', 'bottom_lip_top_center', 'left_eye_center', 'bottom_lip_top_right_midpoint', 'left_eye_center_top', 'left_ear_center', 'top_lip_top_right_midpoint', 'bottom_lip_bottom_left_midpoint', 'right_eye_center_bottom', 'right_eye_bottom_outer_midpoint', 'left_eye_inner_corner', 'right_mouth_outer_corner', 'left_eyebrow_inner_midpoint', 'left_ear_top', 'right_ear_center', 'nose_center_top', 'right_eye_pupil', 'bottom_lip_top_right_center', 'left_eye_center_bottom', 'right_eye_top_inner_midpoint', 'left_cheek_2', 'face_right', 'right_nostril', 'top_lip_top_left_midpoint', 'right_eye_bottom_inner_midpoint', 'left_cheek_1', 'left_cheek_0', 'right_eyebrow_outer_end', 'nose_ridge_top', 'mouth_center', 'left_nostril', 'right_cheek_1', 'right_cheek_0', 'right_cheek_2', 'left_ear_canal']

class FaceImagesDataset(object):
    """
    Base class defining a standard interface to access datasets containing static images of faces and all associated info.
    """

    def __init__(self, dataset_name, relative_base_directory=None):
        """
        Initilizes a dataset with the given name, and whose
        constituent files are located in the specified
        directory. This directory is specified only relative to
        some standard dataset root location (found with locate_data_path ) 
        """
        self.dataset_name = dataset_name
        if relative_base_directory is not None:
            self.relative_base_directory = relative_base_directory
            self.absolute_base_directory = locate_data_path(relative_base_directory)

    def get_name(self):
        return self.dataset_name

    def __len__(self):
        """
        Returns the total number of face examples in the dataset.
        """
        raise NotImplementedError(str(type(self))+" does not implement __len__.")

    def __getitem__(self, i):
        """
        Returns an object that exposes all properties of the ith face example
        Technically it will return an instance of FaceDatasetExample on which
        accessing properties will be handled by calling the corresponding get_... method
        of the current dataset, with parameter i.
        """
        
        if isinstance(i,int):
            if i<0 or i>=self.__len__():
                raise IndexError()
            return FaceDatasetExample(self, i)
                
        elif isinstance(i,slice):
            return FaceImagesSubset(self,range(i.start, i.stop, i.step))

        else: # assume list of indexes
            li = [idx for idx in i] # build list fro any iterable
            return FaceImagesSubset(self,li)

    def get_original_image(self, i):
        filepath = self.get_original_image_path(i)
        img = cv.LoadImage(filepath)
        return img

    def get_original_image_path(self,i):
        """
        Returns a full path from where to load the original image
        """
        relpath = self.get_original_image_path_relative_to_base_directory(i)
        return os.path.join(self.absolute_base_directory, relpath)
    
    def verify_samples(self, i=None):
        '''
        displays sample image with keypoints and bounding boxes 
        and all the information that is there is displayes
        '''
        entered = False
        while(True):
            index1 = 0
              
            if(i==None or entered == True):
                i = index1 + int(numpy.random.random((1)) * self.__len__())
            print 'Dataset Size:', self.__len__()
            print 'Index:', i
            filepath = self.get_original_image_path(i)
            img = Image.open(filepath)
            img.show('Original Image')
            print 'Size:', img.size
            bbox = self.get_bbox(i)
            factorX = 1.0
            factorY = 1.0
            draw = ImageDraw.Draw(img)

            if bbox != None and isinstance(bbox[0], list) and bbox[0] is not None:
                bbox = bbox[0]

            if bbox == None:
                print 'No bounding box information'
            
            else:
                print 'bbox:', bbox
                w,h = (bbox[2]-bbox[0], bbox[3]-bbox[1])
                width, height = img.size
                if w < 200 or h < 200:
                    factorX = 200.0/w
                    factorY = 200.0/h
                    img = img.resize((int(width*factorX), int(height*factorY)))
                
                draw = ImageDraw.Draw(img)
                bbox = [bbox[0]*factorX, bbox[1]*factorY, bbox[2]*factorX, bbox[3]*factorY]
                draw.rectangle(bbox , outline="#FF00FF")

                    
            print 'keypoints:'
            keypoints = self.get_keypoints_location(i)
            if keypoints is None or len(keypoints) == 0:
                print 'No keypoint information available'
            else:
                index = 1
                for key in keypoints:
                    print index, ':' , key, '=', keypoints[key]
                    (x, y ) = keypoints[key]
                    draw.text((x * factorX, y * factorY), str(index))
                    index += 1
            img.show()
            print 'press any q to exit, any other key to continue..'
            ui = sys.stdin.readline()  
            ui = ui.rstrip("\n")
            entered = True
            if ui=="q":  
                return
        

    def get_original_image_path_relative_to_base_directory(self, i):
        """
        Returns the relative path that needs to be concatenated to the
        relative_base_directory (which locates this dataset's directory) 
        in order to access the image file containing the ith face example.
        """
        raise NotImplementedError()

    def get_pan_tilt_and_roll(self, i):
        """
        Return a tuple that contains (Pan Angle/value, Tilt Angle/value, Role Angle/value)
        where Pan angle can be from -90:90 degree (left to right from  subject's perspective)
        and Tilt Angle can be from -90:90 (bottom to top)
        Roll is head tilt angle side ways.Tilting towards left means negative angle. Upright head is 0 roll.
        Eg: (-45,-45, 0) a person is looking to his left-bottom
        """
        raise NotImplementedError()

    def get_index_from_image_filename(self, imgFileName):
        """
        Returns the index number of the image named 'imgFileName' so that we can call methods that take
        "ith face" index as a parameter.

        imgFileName is usually only the filename. When dataset use the same file names in different folders for various
        images, then imgFileName is the shortest path to distinguish all images.
        """
        pass

    def get_bbox(self, i):
        """
        Returns a list of a bounding box around the faces in the ith image,
        as recorded (or precomputed) in the dataset. Returns None if not available.

        This is necessary for datasets with images that contain several faces,
        And relevant for databases that could be used for training a face detector.

        Default version returns the first one of get_orginal_bbox, get_picasa_bbox, get_opencv_bbox that is not None
        Subclasses should override one or several of these as appropriate.
        """
        bbox = self.get_original_bbox(i)
        if bbox is None:
            bbox = self.get_picasa_bbox(i)
            if bbox is None:
                bbox = self.get_opencv_bbox(i)
        return bbox
    
    def get_opencv_bbox(self, i):
        return None

    def get_original_bbox(self, i):
        return None

    ## Access to Picasa precomputed bounding boxes

    def set_picasa_path_substitutions(self, search_replace, csv_delimiter=' '):
        """Defines how to transform an image filepath into the corresponding filepath for the picasa bounding box"""
        self.picasa_search_replace = search_replace
        self.picasa_csv_delimiter = csv_delimiter
        
    def get_picasa_path_from_image_path(self, imagepath):
        """Transforms an (absolute) imagepath into the path to the file containing bounding box info precomputed by picasa
        Default version simply performs all substitutions in property picasa_search_replace, if it exists. Reuturns None otherwise.
        """
        if hasattr(self, 'picasa_search_replace'):
            return search_replace(imagepath, self.picasa_search_replace)
        return None

    def get_picasa_bbox(self, i):
        """Returns a list of bouhnding boxes precomputed by picasa.

        Default version calls get_picasa_path_from_image_path
        to locate the file containing the precomputed bounding box info"""
        imagepath = self.get_original_image_path(i)
        # pdb.set_trace()
        bboxpath = self.get_picasa_path_from_image_path(imagepath)
        if bboxpath is not None and os.path.exists(bboxpath):
            bboxes = []
            with open(bboxpath) as f:
                reader = csv.reader(f, delimiter=self.picasa_csv_delimiter)
                for row in reader:
                    bboxes.append([float(x) for x in row[:4]])
            return bboxes

        return None
    
    def get_eyes_location(self, i):
        """
        Returns the location of the center of the two eyes, in imge coordinates, as a tuple
        (left_x, left_y, right_x, right_y) in that order or None if not available.
        left means the leftmost eye on the image (usually corresponding to the person's right eye).
        Coordinate system has its origin in the upper left corner of the image (horizontal_offset_in_pixels,vertical_offset_in_pixels).
        """
        return None

    def get_keypoints_location(self, i):
        """
        Returns a dictionary of keypoint_names -> (x,y) image coordinates (or None if not available).
        Coordinate system has its origin in the upper left corner of the image
            (horizontal_offset_in_pixels, vertical_offset_in_pixels).

        Possible names for the keypoints should be one of FGNet definition :
        *** Left = left of subject therefore at the right of the image in frontal view ***

        left_eyebrow_inner_end
        mouth_top_lip_bottom
        right_ear_canal
        right_ear_top
        mouth_top_lip
        mouth_bottom_lip_top
        right_eyebrow_center
        chin_left
        nose_tip
        left_eyebrow_center_top
        left_eye_outer_corner
        right_ear
        mouth_bottom_lip
        left_eye_center
        left_mouth_outer_corner
        left_eye_center_top
        left_ear_center
        nostrils_center
        right_eye_outer_corner
        right_eye_center_bottom
        chin_center
        left_eye_inner_corner
        right_mouth_outer_corner
        left_ear_bottom
        right_eye_center_top
        right_eyebrow_inner_end
        left_eyebrow_outer_end
        left_ear_top
        right_ear_center
        nose_center_top
        face_center
        right_eye_inner_corner
        right_eyebrow_center_top
        left_eyebrow_center
        right_eye_pupil
        right_ear_bottom
        mouth_left_corner
        left_eye_center_bottom
        left_eyebrow_center_bottom
        mouth_right_corner
        right_nostril
        right_eye_center
        chin_right
        right_eyebrow_outer_end
        left_eye_pupil
        mouth_center
        left_nostril
        right_eyebrow_center_bottom
        left_ear_canal
        left_ear
        face_right
        face_left
        (NOTE: a list of those keypoints formated as a python list is available in 
            emotiw/keypoints_desc/keypoints_desc)

        """
        return None


    ## Access to Ramanan precomputed keypoints

    def set_ramanan_path_substitutions(self, search_replace):
        """Defines how to transform an image filepath into the corresponding filepath containing ramanan precomputed keypoints"""
        self.ramanan_search_replace = search_replace

    def get_ramanan_path_from_image_path(self, imagepath):
        """Transforms an (absolute) imagepath into the path to the file containing keypoints precomputed by Ramanan's algorithm
        Default version simply performs all substitutions in property ramanan_search_replace, if it exists. Reuturns None otherwise.
        """
        if hasattr(self, 'ramanan_search_replace'):
            return search_replace(imagepath, self.ramanan_search_replace)
        return None

    def get_ramanan_keypoints_location(self, i):
        """Returns a dictionary of keypoints precomputed by Ramanan's algorithm
        Default version calls get_ramanan_path_from_image_path to locate the file containing this info.
        """        
        imagepath = self.get_original_image_path(i)
        # pdb.set_trace()
        ramananpath = self.get_ramanan_path_from_image_path(imagepath)
        if ramananpath is not None and os.path.exists(ramananpath):
            matfile = sio.loadmat(ramananpath)
            xs = matfile['xs'][0]
            ys = matfile['ys'][0]
            # pdb.set_trace()

            return dict([ ("ramanan_%d"%pos, coord) for pos,coord in enumerate(zip(xs,ys)) ])

            # The following correspondances were taken from the code in MultiPie, but apparently they do not correctly match those returned by Ramanan's procedure
            # pts_idx_dict_68 = {0: 'right_ear_top', 1: 'right_ear_center', 2: 'right_ear_bottom', 7: 'chin_right', 8: 'chin_center', 9: 'chin_left', 14: 'left_ear_bottom', 
            #                     15: 'left_ear_center', 16: 'left_ear_top', 17: 'right_eyebrow_outer_end', 19: 'right_eyebrow_center', 21: 'right_eyebrow_inner_end', 
            #                     22: 'left_eyebrow_inner_end', 24: 'left_eyebrow_center', 26: 'left_eyebrow_outer_end', 27: 'nose_center_top', 30: 'nose_tip', 31: 'right_nostril', 
            #                     34: 'nostrils_center', 35: 'left_nostril', 36: 'right_eye_outer_corner', 39: 'right_eye_inner_corner', 42: 'left_eye_inner_corner', 45: 'left_eye_outer_corner', 
            #                     48: 'mouth_right_corner', 51: 'mouth_top_lip', 54: 'mouth_left_corner', 57: 'mouth_bottom_lip', 62: 'mouth_center'}             

            # pts_idx_dict_39 = {0: 'nose_center_top', 3: 'nose_tip', 4: 'nostrils_center', 5: 'left_nostril', 6: 'left_eyebrow_outer_end', 9: 'left_eyebrow_inner_end', 10: 'left_eye_outer_corner', 
            #                     15: 'mouth_top_lip', 18: 'mouth_left_corner', 21: 'mouth_bottom_lip', 22: 'mouth_center', 29: 'chin_center', 36: 'left_ear_bottom', 37: 'left_ear_center', 38: 'left_ear_top'}

            # translation_dict = pts_idx_dict_68
            
            # if len(xs) < 68:
            #     translation_dict = pts_idx_dict_39

            # keypoint_dict = {}
            # for i in xrange(len(xs)):
            #     name = translation_dict.get(i, 'point_'+str(i))
            #     keypoint_dict[name] = (xs[i], ys[i])

            # return keypoint_dict

        return None                    

    def get_n_subjects(self):
        """
        Returns how many different subjects are in the database (or None if unknown)
        """
        return None

    def get_id_of_kth_subject(self, k):
        """
        Retruns a string uniquely identifying the kth subject from this database (or None if unknown)
        """
        return k

    def get_face_examples_for_subject(self, k):
        """
        Returns a list of indexes of all face examples associated with the kth subject.
        Returns None if id info not available.
        """
        id = self.get_id_of_kth_subject(k)
        if id is None:
            return None
        matching_example_indexes =  [ i for i in range(len(self)) if self.get_subject_id_of_ith_face(i)==id ] 
        return matching_example_indexes

    def get_subject_id_of_ith_face(self, i):
        """
        Returns a string that uniquely identifies the identity of the subject in the ith face of this dataset.
        Returns None if this information is not available.
        """
        return None

    def get_detailed_emotion_label(self, i):
        """
        Returns a string containing detailed emotion label associateed to the ith face
        returns None is not available.

        Default version calls get_7emotion_label.
        """
        return self.get_7emotion_label(i)

    def get_7emotion_label(self, i):
        """
        Returns a string containing one of the 7 basic emotion labels associatedto the ith face examples
        returns None is not available.
        'anger', 'disgust', 'fear', 'happy', 'sad', 'surprise', 'neutral'

        Default version returns the name associated to numerical index returned by get_7emotion_index
        """
        emo_index = self.get_7emotion_index(i)
        if emo_index is None or emo_index<0:
            return None
        else:
            return basic_7emotion_names[emo_index]

    def get_7emotion_index(self, i):
        """
        Returns the emotion index for the ith image.
        Indexes are : 
            0 : anger
            1 : disgust
            2 : fear
            3 : happy
            4 : sad
            5 : surprise
            6 : neutral
        Returns None if this information is not available or the provided emotion is unrelated
        to the 7 emotions defined above.
        """
        return None

    def get_facs(self, i):
        """
        Returns the facial action coding system for the ith image (or None if not available).
        http://en.wikipedia.org/wiki/Facial_Action_Coding_System

        Returns a dictionary:
        keys are the action unit codes for the action units that were observed,
        its associated values are intensity scoring 'A', 'B', 'C', 'D', or 'E' or None if the intensity score is not known.
        """
        return None

    def get_head_pose(self, i):
        """
        Returns the head pose relative to the camera (or None if not available)
        
        The pose is described, for now, as an integer value between 0 and 8
        indicating the direction the subject's head is facing. Each of these
        integer values is associated with a quadrant as shown in the square
        below :
          0 1 2
        9 3 4 5 10
          6 7 8
        
        For instance : 
        1 means the subject is looking up
        3 means the subject is looking to his right (left of the camera) at about 45 degrees
        4 means the subject is looking directly at the camera 
        8 means the subject is looking down to his left (right of the camera)
        9 means profile view (the subject is looking to his right (left of the camera) at about 90 degrees
        ...
        """
        return None

    def get_light_source_direction(self, i):
        """
        Returns the direction of the light source (or None if not available)
        """
        return None

    def get_gaze_direction(self, i):
        """
        Returns the direction in which the person was looking (or None if not available)
        """
        return None

    def get_gender(self,i):
        """
        Returns either male of female if available
        """
        return None

    def get_is_mouth_opened(self, i):
        """
        Returns True if the mouth is opened. False if it's not.
        Returns None if this is not defined on the dataset
        """
        return None

    def get_standard_train_test_splits(self):
        """Returns a list of pairs (train_indexes, test_indexes) where train_indexes and test_indexes are themselves lists or integer ndarrays
        (containing indexes that can be passed to e.g. get_original_image_path)
        Returns None if not available"""
        return None

    def count(self, method):
        """Counts the number of times the givenmethod returns None or raises an error
        Returns a triple (n_not_None, n_None, n_errors) of the times over the __len__ examples,
        that the method returned None or raised an error.
        Ex:
        dataset.count(dataset.get_facs)
        """

        not_none_count = 0
        none_count = 0
        error_count = 0
        for i in xrange(self.__len__()):
            try:
                feature = method(i)
                if feature is None:
                    none_count += 1
                else:
                    not_none_count += 1
            except:
                error_count += 1
        return (not_none_count, none_count, error_count)
        

    def count_values(self, method):
        """Returns a dictionary mapping values returned by a method call to their count over the __len__ examples
        Ex:
        dataset.count_values(dataset.get_7emotion_label)
        """
        counts = {}
        for i in xrange(self.__len__()):
            try:
                feature = method(i)
            except:
                pass
            if feature not in counts:
                counts[feature] = 1
            else:
                counts[feature] += 1
        return counts

    def print_info(self, out=sys.stdout):
        """Prints various info and statistics about this dataset, such as class counts"""

        length = self.__len__()
        print >>out, "**********************************************"
        print >>out, "FACE IMAGE DATASET ", self.get_name()
        print >>out, "length (# examples):", length
        print >>out, "n_subjects:", self.get_n_subjects()

        # report split counts
        splits = self.get_standard_train_test_splits()
        splitcounts = None
        if splits is not None:
            splitcounts = []
            for split in splits:
                splitcounts.append( [ len(indices) for indices in split ] )
        print >>out, "standard splits:"
        print >>out, splitcounts
        print >>out

        # count number of features available

        feature_list = ["bbox",
                        "picasa_bbox",
                        "opencv_bbox",
                        "original_bbox",
                        "eyes_location",
                        "keypoints_location",
                        "facs" ]

        for feature_name in feature_list:
            method = getattr(self, "get_"+feature_name)
            not_none_count, none_count, error_count = self.count(method)
            print >>out, "%25s: %6d / %d \t (%.2f%%, %d None, %d errors)" % \
                  (feature_name, not_none_count, length, 100.0*not_none_count/length, none_count, error_count)
        print >>out
        
        # class counts and proportions
        feature_list = ["7emotion_label",
                        "7emotion_index",
                        "subject_id_of_ith_face",
                        "detailed_emotion_label",
                        "head_pose",
                        "light_source_direction",
                        "gaze_direction",
                        "gender",
                        "is_mouth_opened"]
        for feature_name in feature_list:
            method = getattr(self, "get_"+feature_name)
            not_none_count, none_count, error_count = self.count(method)
            print >>out, "%25s: %6d / %d \t (%.2f%%, %d None, %d errors)" % \
                  (feature_name, not_none_count, length, 100.0*not_none_count/length, none_count, error_count)
            
            if not_none_count>0:
                values_counts = self.count_values(method)
                for val in values_counts:
                    if val is not None:                        
                        print >>out, "%30s: %6d / %d \t (%.2f%%)" % (val, values_counts[val], not_none_count, 100.0*values_counts[val]/not_none_count)
            print >>out


# Helper classes

class FaceImagesSubset(FaceImagesDataset):
    """
    A subset view of a FaceImagesDataset. This view is itself a FaceImagesDataset.
    """
    def __init__(self, img_dataset, indices, dataset_name=None):
        if dataset_name is None:
            dataset_name = "subset of "+img_dataset.get_name()
        super(FaceImagesSubset,self).__init__(dataset_name)
        self.img_dataset = img_dataset
        self.indices = indices
        
    def __len__(self):
        return len(self.indices)
        
    def get_original_image_path(self,i):
        return self.img_dataset.get_original_image_path(self.indices[i])
    
    def get_original_image_path_relative_to_base_directory(self, i):
        return self.img_dataset.get_original_image_path_relative_to_base_directory(self.indices[i])
    
    def get_bbox(self, i):
        return self.img_dataset.get_bbox(self.indices[i])
    
    def get_eyes_location(self, i):
        return self.img_dataset.get_eyes_location(self.indices[i])
    
    def get_keypoints_location(self, i):
        return self.img_dataset.get_keypoints_location(self.indices[i])    
    
    def get_subject_id_of_ith_face(self, i):
        return self.img_dataset.get_subject_id_of_ith_face(self.indices[i])
    
    def get_detailed_emotion_label(self, i):
        return self.img_dataset.get_detailed_emotion_label(self.indices[i])
    
    def get_7emotion_label(self, i):
        return self.img_dataset.get_7emotion_label(self.indices[i])
    
    def get_7emotion_index(self, i):
        return self.img_dataset.get_7emotion_index(self.indices[i])
    
    def get_facs(self, i):
        return self.img_dataset.get_facs(self.indices[i])
    
    def get_head_pose(self, i):
        return self.img_dataset.get_head_pose(self.indices[i])
    
    def get_light_source_direction(self, i):
        return self.img_dataset.get_light_source_direction(self.indices[i])
    
    def get_gaze_direction(self, i):
        return self.img_dataset.get_gaze_direction(self.indices[i])
    
    def get_gender(self,i):
        return self.img_dataset.get_gender(self.indices[i])
    
    def get_is_mouth_opened(self, i):
        return self.img_dataset.get_is_mouth_opened(self.indices[i])

    def _get_subject_ids(self):
        if hasattr(self,subject_ids):
            return self.subject_ids

        subject_ids = []
        for i in xrange(len(self)):
            id = self.get_subject_id_of_ith_face(i)
            if id is not None and id not in subject_ids:
                subject_ids.append(id)
        if len(subject_ids)==0:
            self.subject_ids = None
        else:
            self.subject_ids = subject_ids
        return self.subject_ids
    
    def get_n_subjects(self):
        """
        Returns how many different subjects are in the database (or None if unknown)
        """
        subject_ids = self._get_subject_ids()
        if subject_ids is None:
            return None
        return len(subject_ids)

    def get_id_of_kth_subject(self, k):
        """
        Retruns a string uniquely identifying the kth subject from this database (or None if unknown)
        """
        subject_ids = self._get_subject_ids()
        if subject_ids is None:
            return None
        return subject_ids[k]


class FaceDatasetExample(object):
    """
    A view of a single example of a FaceImagesDataset
    Presented as an object with properties.
    Property names match accessor methods of the FaceImagesDataset.
    """
    
    property_names = frozenset([
        "original_image",
        "original_image_path",
        "original_image_path_relative_to_base_directory",
        "bbox",
        "eyes_location",
        "keypoints_location",
        "subject_id_of_ith_face",
        "detailed_emotion_label",
        "7emotion_label",
        "7emotion_index",
        "facs",
        "head_pose",
        "light_source_direction",
        "gaze_direction",
        "gender",
        "is_mouth_opened"
        ])
    
    def __init__(self, dataset, i):
        self._dataset = dataset
        self._i = i
        
    def __getattr__(self, property_name):
        if property_name in FaceDatasetExample.property_names:            
            dataset_method = getattr(self._dataset, "get_"+property_name)
            return dataset_method(self._i)
        else:
            raise AttributeError()

