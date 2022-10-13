"""
Shape detection implementation for
the geology-cuantifier project.
"""

from typing import List, Tuple
import cv2, numpy as np

COLORS = [(255,0,0), (0,255,0), (0,0,255)]
STATISTICS = ["Area", "Radio Equiv", "Largo Equiv", "Punto Medio X", "Punto Medio Y"]

class ContourData(object):
    """
    This class is in charge of holding
    relevant data of a contour, such as 
    It's bounding rectangle and a mask
    with only the pixels in that region.
    """

    def __init__(self, img, contour) -> None:
        """
        Class constructor, instantiates class
        params. such as the bounding rect. of a contour
        and It's mask.
        """
        self.img = img
        self.contour = contour
        self.r = cv2.boundingRect(contour)
        self.group = None

    def aspect_ratio(self) -> float:
        """
        When called, this function returns
        the aspect ratio of the bounding rect
        of the contour.
        """
        _, _, w, h = self.r
        return w/h
    
    def get_area(self) -> float:
        """
        When called, this function returns
        the total area of the contour.
        """
        return cv2.contourArea(self.contour)
    
    def get_equiv_radius(self) -> float:
        """
        When called, this function returns
        the equivalent radius associated to 
        the area of the contour.
        """
        return np.sqrt(self.get_area()/np.pi)
    
    def get_equiv_lenght(self) -> float:
        """
        When called, this function returns
        the equivalent lenght associated to 
        the area of the contour.
        """
        return np.sqrt(self.get_area()/self.aspect_ratio())

    def get_middle_point(self) -> Tuple[float, float]:
        """
        When called, this function returns
        the middle point of the bounding rect
        of the contour.
        """
        x, y, w, h = self.r
        return (x+w/2, y+h/2)
    
    def get_all_statistics(self) -> List:
        """
        When called, this function returns
        the results of all statistics implemented
        in the class.
        """
        return [
            self.group,
            self.get_area(), 
            self.get_equiv_radius(), 
            self.get_equiv_lenght(), 
            self.get_middle_point()[0],
            self.get_middle_point()[1],
            ]

def contour_segmentation(img):
    """
    Finds the contours of the image, for each computes
    It's bounding rect and mask. Then draws the contours 
    and returns a list with all the data.
    """
    data = []
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    (_, threshInv) = cv2.threshold(gray, 1, 255,cv2.THRESH_BINARY)

    contours, _ = cv2.findContours(threshInv, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for cnt in contours:
        mask = np.zeros(img.shape[:2], dtype="uint8")
        r = cv2.boundingRect(cnt)
        cv2.drawContours(mask, [cnt],-1, (255,255,255),-1)
        masked = cv2.bitwise_and(img,img, mask = mask)
        # x,y,w,h = r
        # masked = masked[y:y+h, x:x+w]
        data.append(ContourData(masked,cnt))
    return data

def contour_agrupation(contours):
    """
    Runs a basic agrupation by comparing the aspect ratio
    of each contour's bounding rect.
    """
    for c in contours:
        asp_rat = c.aspect_ratio()
        if asp_rat <= 1.2 and asp_rat >= 0.8:
            # Square like rectangles
            c.group = 0
        elif asp_rat <= 1.5 and asp_rat >= 0.5:
            c.group = 1
        else:
            c.group = 2

def cluster_segmentation(cluster, contours):
    """
    Once each CountourData instance is successfully 
    agrupated, this function draws each bounding rect.
    
    The rectangle colour will be given by the group of the 
    ContourData instance.
    """
    im = np.copy(cluster)
    for c in contours:
        color = COLORS[c.group]
        cv2.rectangle(im, c.r, color, 2)
    return im

def generate_results(contours):
    """
    Calculate statistics for each group.
    """
    final_results = []
    for c in contours:
        final_results.append(c.get_all_statistics())
    return final_results

def image_agrupation(contours,groups):
    """
    Agrupate all images of the contours in one image for each group
    """
    shape = contours[0].img.shape
    masks = [np.zeros(shape, dtype="uint8")]*groups
    for i in range(len(contours)):
        group = contours[i].group
        # img_r = np.resize(masks[group],shape)
        masks[group] =  cv2.add(contours[i].img, masks[group])
    for i in range(len(contours)):
        group = contours[i].group
        x, y, w, h =contours[i].r
        position = (x,y)
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_size = 0.3
        font_color = (221,82,196)
        font_thickness = 1
        cv2.putText(masks[group],str(i), position, font, font_size, font_color, font_thickness)
    return masks
