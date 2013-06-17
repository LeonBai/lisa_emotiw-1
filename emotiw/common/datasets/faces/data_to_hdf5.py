import tables
import PIL.Image
from crop_face import crop_face
from faceimages import FaceDatasetExample, keypoints_names

class ImgStruct(tables.IsDescription):
    data = tables.StringCol(96*96*3)

class LabelStruct(tables.IsDescription):
    name = tables.Int8Col()
    col = tables.Float64Col()
    row = tables.Float64Col()

def to_hdf5(wrapper, save_as=None):
    if save_as is None:
        save_as = wrapper.dataset_name.replace(' ', '_') + '.h5'

    keypoints_to_id = {'left_eyebrow_inner_end': 1, 'left_eyebrow_outer_end': 27, 'mouth_top_lip_bottom': 2, 'right_ear_canal': 3, 'face_right': 52, 'right_ear_top': 4, 'right_ear_center': 29, 'mouth_top_lip': 5, 'right_eye_center_top': 25, 'mouth_bottom_lip_top': 6, 'right_eyebrow_center': 7, 'face_center': 31, 'chin_left': 8, 'right_eyebrow_center_top': 33, 'face_left': 53, 'left_eyebrow_center': 34, 'right_eye_pupil': 35, 'right_nostril': 42, 'mouth_left_corner': 37, 'left_eye_center_bottom': 38, 'nose_tip': 9, 'nostrils_center': 18, 'left_eyebrow_center_top': 10, 'left_eye_outer_corner': 11, 'mouth_right_corner': 41, 'right_eye_inner_corner': 32, 'left_nostril': 48, 'right_eye_center': 43, 'right_ear': 12, 'left_ear_top': 28, 'mouth_bottom_lip': 13, 'left_eye_center': 14, 'left_mouth_outer_corner': 15, 'right_eyebrow_outer_end': 45, 'left_eye_center_top': 16, 'left_ear_center': 17, 'left_eye_pupil': 46, 'left_eyebrow_center_bottom': 39, 'right_ear_bottom': 36, 'right_eyebrow_inner_end': 26, 'right_eye_center_bottom': 20, 'chin_center': 21, 'left_eye_inner_corner': 22, 'mouth_center': 47, 'right_mouth_outer_corner': 23, 'left_ear_bottom': 24, 'nose_center_top': 30, 'right_eyebrow_center_bottom': 49, 'left_ear_canal': 50, 'right_eye_outer_corner': 19, 'left_ear': 51, 'chin_right': 44}
    
    f = None

    print wrapper.dataset_name
 
    try:
        f = tables.openFile(save_as, mode='w')

        train_group = f.createGroup('/', 'train', 'train set')
        test_group = f.createGroup('/', 'test', 'test set')

        img_groups = (train_group, None)

        test_idx = None
        dsets = [range(len(wrapper)), None]

        if wrapper.get_standard_train_test_splits() is not None:
            dsets[0], dsets[1] = wrapper.get_standard_train_test_splits()
            img_groups = (img_groups[0], test_group)

        for some_idx, testing in enumerate(dsets):
            if testing is None: 
                break
            img_group = img_groups[some_idx]
            dset = dsets[some_idx]

            img_table = f.createCArray(img_group, 'img', tables.StringAtom(itemsize=1), shape=(len(dset), 96*96*3))
            label_table = f.createCArray(img_group, 'label', tables.Float64Atom(), shape=(len(dset), len(keypoints_names), 2))

            for i, _ in enumerate(dset):
                #img_table = f.createTable(this_group, 'img', ImgStruct, 'image data')
                #label_table = f.createTable(this_group, 'label', LabelStruct, 'target data')

                                #img_row = img_table.row
                #label_row = label_table.row

                img, label = crop_face(PIL.Image.open(wrapper.get_original_image_path(i)),
                                            wrapper.get_bbox(i),
                                            wrapper.get_eyes_location(i),
                                            wrapper.get_keypoints_location(i))
                 
                #img_row['data'] = img.tostring()
                #img_row.append()
                img_table[i, :] = img.tostring()
                for name, point in label.iteritems():
                    label_table[i, keypoints_names.index(name), :] = [point[0], point[1]]

                    #the_id = keypoints_names.index(name)
                    #The name of the keypoint MUST be in keypoints_names by
                    #definition.

                    #label_row['name'] = the_id
                    #label_row['col'] = point[0]
                    #label_row['row'] = point[1]
                    #label_row.append()
                #img_table.flush()
                #label_table.flush()

    finally:
        if f is not None:
            f.close()
