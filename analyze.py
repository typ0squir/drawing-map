import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# Load the image
img = cv2.imread('map.png')
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# The background is white (255, 255, 255).
# The boundary is thick grey.
# The booths are colored rectangles, with white grid lines inside.

# Let's find the grid size by analyzing distances between white lines inside a booth.
# But first, let's find the booths.
# A booth is any non-white, non-grey region.
# Let's threshold it: everything that is not close to white.
_, mask = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)

# Remove the grey boundary: the grey boundary is typically around 150-200.
# Let's check unique colors or just filter by color.
hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
# Booths have some saturation. Grey has very low saturation.
saturation = hsv[:, :, 1]
_, mask_color = cv2.threshold(saturation, 10, 255, cv2.THRESH_BINARY) # only colored regions

# Find contours of the booths
contours, _ = cv2.findContours(mask_color, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

booths = []
for cnt in contours:
    x, y, w, h = cv2.boundingRect(cnt)
    if w > 20 and h > 20: # filter out noise
        booths.append((x, y, w, h))

print(f"Found {len(booths)} booth blocks.")

# Now we need to find the unit size. The white lines inside the booths are the grids.
# Let's pick a large booth and find the horizontal and vertical white lines.
unit_w, unit_h = 0, 0
for (x, y, w, h) in booths:
    # extract the booth image
    booth_img = gray[y:y+h, x:x+w]
    # find vertical white lines: columns that are mostly white
    white_cols = np.where(np.mean(booth_img, axis=0) > 240)[0]
    white_rows = np.where(np.mean(booth_img, axis=1) > 240)[0]
    
    # find differences between consecutive white lines
    if len(white_cols) > 0:
        diffs = np.diff(white_cols)
        # distances between lines > 10 pixels
        valid_diffs = diffs[diffs > 10]
        if len(valid_diffs) > 0:
            unit_w = np.median(valid_diffs)
    
    if len(white_rows) > 0:
        diffs = np.diff(white_rows)
        # distances between lines > 10 pixels
        valid_diffs = diffs[diffs > 10]
        if len(valid_diffs) > 0:
            unit_h = np.median(valid_diffs)
            
    if unit_w > 0 and unit_h > 0:
        break

print(f"Estimated unit size: {unit_w} x {unit_h}")

# If we couldn't estimate, let's just make a guess or maybe the boxes themselves are multiples.
# Let's sort the widths and heights of all booths and find the greatest common divisor or minimum.
widths = [w for _, _, w, _ in booths]
heights = [h for _, _, _, h in booths]
if unit_w == 0:
    unit_w = min(widths)
if unit_h == 0:
    unit_h = min(heights)

print(f"Final unit size: {unit_w} x {unit_h}")

# Draw the result
out_img = img.copy()

# For font, try to use a default or just cv2.putText
for (x, y, w, h) in booths:
    # Calculate units
    uw = max(1, round(w / unit_w))
    uh = max(1, round(h / unit_h))
    area = uw * uh
    
    text = f"{uw}x{uh} ({area})"
    
    # Draw bounding box
    cv2.rectangle(out_img, (x, y), (x+w, y+h), (0, 0, 255), 2)
    
    # Draw text
    font_scale = 0.5
    thickness = 1
    (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
    
    # center text
    tx = x + (w - tw) // 2
    ty = y + (h + th) // 2
    cv2.putText(out_img, text, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 0, 0), thickness+1, cv2.LINE_AA)
    cv2.putText(out_img, text, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), thickness, cv2.LINE_AA)

# Also find the hall boundary (the largest grey rectangle)
# Grey is low saturation, low value? Let's threshold grey
grey_mask = cv2.inRange(hsv, np.array([0, 0, 100]), np.array([180, 50, 200]))
contours, _ = cv2.findContours(grey_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
if contours:
    # Find the largest contour
    largest_cnt = max(contours, key=cv2.contourArea)
    rx, ry, rw, rh = cv2.boundingRect(largest_cnt)
    print(f"Hall boundary: {rw} x {rh}")
    cv2.rectangle(out_img, (rx, ry), (rx+rw, ry+rh), (255, 0, 0), 3)

cv2.imwrite('output.png', out_img)
print("Saved output.png")
