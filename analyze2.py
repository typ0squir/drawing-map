import cv2
import numpy as np

img = cv2.imread('map.png')
hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# White: S < 10, V > 200
# Grey: S < 10, V < 200
# Black/Text: V < 100
# Colored (booths): S > 10, V > 100

colored_mask = (hsv[:, :, 1] > 10) & (hsv[:, :, 2] > 100)
colored_mask = colored_mask.astype(np.uint8) * 255

# Save mask to see
cv2.imwrite('mask_colored.png', colored_mask)

# Group cells belonging to the same booth block.
# The grid lines are white, about 1-3 pixels wide. Let's dilate by 3, then erode by 3.
kernel = np.ones((5, 5), np.uint8)
closed_mask = cv2.morphologyEx(colored_mask, cv2.MORPH_CLOSE, kernel)
cv2.imwrite('mask_closed.png', closed_mask)

contours, _ = cv2.findContours(closed_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

out = img.copy()
blocks = []
for cnt in contours:
    x, y, w, h = cv2.boundingRect(cnt)
    if w > 10 and h > 10:
        blocks.append((x, y, w, h))
        cv2.rectangle(out, (x, y), (x+w, y+h), (0, 0, 255), 2)

print(f"Found {len(blocks)} blocks")
cv2.imwrite('output2.png', out)

# Find unit size. Before closing, the colored mask consists of individual unit cells
# interrupted by text. Let's find contours of colored_mask directly.
contours_cells, _ = cv2.findContours(colored_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
widths = []
heights = []
for cnt in contours_cells:
    x, y, w, h = cv2.boundingRect(cnt)
    if w > 10 and h > 10:
        widths.append(w)
        heights.append(h)

# The most common width and height might be the unit cell minus text interruptions, 
# but let's just use median of combinations. Or maybe pick a clean cell.
# A better way to find unit size:
# For each block, count the number of white columns/rows dividing it.
# A white column in a block is a column where the original image is mostly white.

unit_w, unit_h = 0, 0
all_vw = []
all_vh = []

for (x, y, w, h) in blocks:
    block_gray = gray[y:y+h, x:x+w]
    # white pixels are > 240
    white_mask = (block_gray > 240).astype(np.uint8)
    
    # average along columns
    col_mean = np.mean(white_mask, axis=0)
    # A grid line is where col_mean is high (e.g. > 0.8)
    grid_cols = np.where(col_mean > 0.8)[0]
    
    if len(grid_cols) > 0:
        diffs = np.diff(grid_cols)
        valid = diffs[diffs > 20] # a unit is at least 20px wide
        if len(valid) > 0:
            all_vw.extend(valid)
            
    row_mean = np.mean(white_mask, axis=1)
    grid_rows = np.where(row_mean > 0.8)[0]
    if len(grid_rows) > 0:
        diffs = np.diff(grid_rows)
        valid = diffs[diffs > 20]
        if len(valid) > 0:
            all_vh.extend(valid)

if all_vw:
    unit_w = np.median(all_vw)
if all_vh:
    unit_h = np.median(all_vh)

print(f"Estimated unit size: {unit_w} x {unit_h}")

out_text = img.copy()
from PIL import Image, ImageDraw, ImageFont
pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
draw = ImageDraw.Draw(pil_img)

# Try loading a korean font if possible, else default
try:
    font = ImageFont.truetype("malgun.ttf", 15)
except:
    font = ImageFont.load_default()

for (x, y, w, h) in blocks:
    uw = int(round(w / unit_w)) if unit_w else 1
    uh = int(round(h / unit_h)) if unit_h else 1
    uw = max(1, uw)
    uh = max(1, uh)
    text = f"{uw}x{uh} ({uw*uh})"
    
    # draw box
    draw.rectangle([x, y, x+w, y+h], outline="red", width=2)
    # draw text at center
    # get text bounding box
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    
    tx = x + (w - tw)//2
    ty = y + (h - th)//2
    
    # outline text
    draw.text((tx-1, ty), text, fill="white", font=font)
    draw.text((tx+1, ty), text, fill="white", font=font)
    draw.text((tx, ty-1), text, fill="white", font=font)
    draw.text((tx, ty+1), text, fill="white", font=font)
    draw.text((tx, ty), text, fill="black", font=font)

cv2.imwrite('output3.png', cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR))
print("Saved output3.png")

# Boundary detection
grey_mask = ((hsv[:, :, 1] < 20) & (hsv[:, :, 2] < 200) & (hsv[:, :, 2] > 100)).astype(np.uint8)*255
cv2.imwrite('mask_grey.png', grey_mask)
contours, _ = cv2.findContours(grey_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
if contours:
    largest_cnt = max(contours, key=cv2.contourArea)
    rx, ry, rw, rh = cv2.boundingRect(largest_cnt)
    print(f"Hall boundary box: x={rx}, y={ry}, w={rw}, h={rh}")
    
    # Compute boundary area in units if unit_w and unit_h are found
    if unit_w and unit_h:
        total_uw = round(rw / unit_w)
        total_uh = round(rh / unit_h)
        print(f"Hall boundary units: {total_uw}x{total_uh} ({total_uw*total_uh} total units)")
