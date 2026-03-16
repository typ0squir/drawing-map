import cv2
import numpy as np

img = cv2.imread('map.png')
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

# Mask for white lines inside the hall
# White: V > 240, S < 10
white_mask = ((hsv[:,:,1] < 15) & (hsv[:,:,2] > 240)).astype(np.uint8) * 255

# Project vertically and horizontally to find lines
col_mean = np.mean(white_mask, axis=0)
row_mean = np.mean(white_mask, axis=1)

# Any column that is mostly white could be a corridor or a grid line.
# We are looking for regular intervals.
import matplotlib.pyplot as plt

plt.figure(figsize=(10,4))
plt.plot(col_mean)
plt.title('Column Mean of White Mask')
plt.savefig('col_mean.png')

plt.figure(figsize=(10,4))
plt.plot(row_mean)
plt.title('Row Mean of White Mask')
plt.savefig('row_mean.png')

print("Saved plots")
