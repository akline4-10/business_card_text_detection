import numpy as np
import pandas as pd
import pytesseract
import cv2
from matplotlib import pyplot as plt
import math
from deskew import determine_skew

# load the image into memory and convert to grayscale
def load_image(filepath):
    return cv2.imread(filepath)

# Extract the text from the image
def extract_all_text(image, confidence = 50):
    data = pytesseract.image_to_data(image)
    data_split = [i.split("\t") for i in data.strip().split("\n")]
    df = pd.DataFrame(data_split[1:], columns = data_split[0])
    for column in df.columns[:-2]:
        df[column] = df[column].astype("int32")
    df["conf"] = df["conf"].astype("float64")
    df['clustered'] = 0
    df['right'] = df.left + df.width
    df['bottom'] = df.top + df.height
    df['center_w'] = df.left + df.width//2
    df['center_h'] = df.top + df.height//2
    mask = (df.text != "") & (df.text.notnull()) & (df.text != " ")
    df2 = df.loc[mask,:]
    
    ## block_num, par_num, line_num
    ### Doesn't need to be a triple for loop...
    text_parts = []
    for block in df2.block_num.unique():
        block_mask = df2.block_num == block
        df_block = df2.loc[block_mask,:]
        for par in df_block.par_num.unique():
            par_mask = df_block.par_num == par
            df_par = df_block.loc[par_mask,:]
            for line in df_par.line_num.unique():
                line_mask = df_par.line_num == line
                df_line = df_par.loc[line_mask,:]
                df_array = np.array(df_line[['left','right','text']])
                line_text = ""
                old_right = df_array[0][0]
                for row in np.array(df_line[['left','right','text']]):
                    left, right, text = row
                    if left - old_right <= 100:
                        line_text += text + " "
                    else:
                        text_parts.append(line_text.strip())
                        line_text = text  + " "
                    old_right = right
                text_parts.append(line_text.strip())
    return text_parts, df

def show(image):
    plt.imshow(image, cmap='gray')
    # plt.axis('off')
    plt.show()

def rotate(image, angle, background):
    old_width, old_height = image.shape[:2]
    angle_radian = math.radians(angle)
    width = abs(np.sin(angle_radian) * old_height) + abs(np.cos(angle_radian) * old_width)
    height = abs(np.sin(angle_radian) * old_width) + abs(np.cos(angle_radian) * old_height)

    image_center = tuple(np.array(image.shape[1::-1]) / 2)
    rot_mat = cv2.getRotationMatrix2D(image_center, angle, 1.0)
    rot_mat[1, 2] += (width - old_width) / 2
    rot_mat[0, 2] += (height - old_height) / 2
    return cv2.warpAffine(image, rot_mat, (int(round(height)), int(round(width))), borderValue=background)

def gray_sharp_thresh(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # blurred = cv2.GaussianBlur(gray, (3,3), 0)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return thresh

def crop_image(image, df, buffer=50):
    (h, w) = image.shape[:2]
    buffer = 50
    left = df.left.min() - buffer
    right = df.left.max() + df.width.max() + buffer
    top = df.top.min() - buffer
    bottom = df.top.max() + df.height.max() + buffer
    if left < 0:
        left = 0
    if top < 0:
        top = 0
    if right > w:
        right = w
    if bottom > h:
        bottom = h
    print(left,right,top,bottom)
    cropped = image[top:bottom,left:right,:]
    return cropped

def preprocess_image(image, debug=False):
    gray = gray_sharp_thresh(image)
    if debug:
        show(gray)
    # Rotate image
    angle = determine_skew(gray)
    if debug:
        print(angle)
    rotated1 = rotate(image, angle, (0, 0, 0))
    rotated2 = rotate(image, -angle, (0, 0, 0))
    if debug:
        show(cv2.cvtColor(rotated1, cv2.COLOR_BGR2RGB))
        show(cv2.cvtColor(rotated2, cv2.COLOR_BGR2RGB))
    ## Extract text
    text1, df1 = extract_all_text(rotated1)
    text2, df2 = extract_all_text(rotated2)
    df3 = df1[(df1.text != "") & (df1.text.notnull()) & (df1.text != " ")]
    df4 = df2[(df2.text != "") & (df2.text.notnull()) & (df2.text != " ")]
    # Crop Image
    if df3.empty and df4.empty:
        raise Exception("Unable to extract text. Upload a better picture, please.")
    elif df3.empty:
        cropped = crop_image(rotated2, df4)
    elif df4.empty:
        cropped = crop_image(rotated1, df3)
    else:
        cropped = crop_image(rotated1, df3)
    
    if cropped.shape[0] > cropped.shape[1]:
        cropped = cv2.rotate(cropped, cv2.ROTATE_90_COUNTERCLOCKWISE)
    if debug:
        show(cv2.cvtColor(cropped, cv2.COLOR_BGR2RGB))
    # Gray, sharpen, and threshold
    final = gray_sharp_thresh(cropped)
    if debug:
        show(final)
    return final


