import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

img = cv2.imread('map.png')
hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
orig_h, orig_w, _ = img.shape

# Hall starts at x=7, y=7
# Wait, let me dynamically find the grey border just in case
grey_mask = ((hsv[:, :, 1] < 20) & (hsv[:, :, 2] < 200) & (hsv[:, :, 2] > 100)).astype(np.uint8)*255
contours, _ = cv2.findContours(grey_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
largest_cnt = max(contours, key=cv2.contourArea)
hx, hy, hw, hh = cv2.boundingRect(largest_cnt)
print(f"Hall boundary: {hx},{hy} - {hw}x{hh}")

# Approximate unit size based on previous findings
unit = int(round(hw / 20)) # 899 / 20 = 45
print(f"Calculated unit pixel size: {unit}")

cols = int(round(hw / unit))
rows = int(round(hh / unit))
print(f"Grid: {cols} x {rows}")

# Create an empty grid to hold color identities
# We will sample the center of each cell.
grid = [[None for _ in range(rows)] for _ in range(cols)]

def color_distance(c1, c2):
    return np.sum(np.abs(np.array(c1, dtype=int) - np.array(c2, dtype=int)))

blocks = [] # List of (set of (i,j) tuples, BGR color)

for i in range(cols):
    for j in range(rows):
        cx = hx + int((i + 0.5) * unit)
        cy = hy + int((j + 0.5) * unit)
        
        # sample a 5x5 area around the center
        patch = hsv[cy-2:cy+3, cx-2:cx+3]
        mean_hsv = np.mean(patch, axis=(0,1))
        
        # if it's not white (S>10) and not grey (V>200 or S>10)
        # Colored booths have saturation > 10
        if mean_hsv[1] > 15 and mean_hsv[2] > 100:
            bgr_color = np.mean(img[cy-2:cy+3, cx-2:cx+3], axis=(0,1)).astype(int)
            bgr_color = tuple(bgr_color)
            
            # Find an existing block with a similar color and adjacent
            found_block = None
            for idx, (cells, c) in enumerate(blocks):
                if color_distance(c, bgr_color) < 20: # similar color
                    # Check if adjacent to any cell in the block
                    is_adj = False
                    for (ci, cj) in cells:
                        if abs(ci - i) <= 1 and abs(cj - j) <= 1:
                            is_adj = True
                            break
                    if is_adj:
                        found_block = idx
                        break
            
            if found_block is not None:
                blocks[found_block][0].add((i, j))
                # update color mean slightly
            else:
                blocks.append((set([(i, j)]), bgr_color))

print(f"Found {len(blocks)} initial blocks")

# Merge adjacent blocks of similar colors (sometimes they process top-left first)
def merge_blocks(blocks):
    merged = True
    while merged:
        merged = False
        for i in range(len(blocks)):
            for j in range(i+1, len(blocks)):
                if color_distance(blocks[i][1], blocks[j][1]) < 30:
                    # check adjacency
                    is_adj = False
                    for c1 in blocks[i][0]:
                        for c2 in blocks[j][0]:
                            if abs(c1[0]-c2[0]) + abs(c1[1]-c2[1]) == 1:
                                is_adj = True
                                break
                        if is_adj: break
                    if is_adj:
                        blocks[i][0].update(blocks[j][0])
                        blocks.pop(j)
                        merged = True
                        break
            if merged: break
    return blocks

blocks = merge_blocks(blocks)
print(f"Merged into {len(blocks)} blocks")

# Now re-draw from scratch
out = np.ones((orig_h, orig_w, 3), dtype=np.uint8) * 255 # start white

# Draw hall boundary (thick grey line)
# Map border is grey
grey_color = (150, 150, 150)
cv2.rectangle(out, (hx-2, hy-2), (hx+hw+2, hy+hh+2), grey_color, 4)

# We can cut a door at the bottom just like the image
cv2.line(out, (hx+hw//5, hy+hh+2), (hx+2*hw//5, hy+hh+2), (255,255,255), 4)

for cells, color in blocks:
    # bounding box in grid
    min_i = min(c[0] for c in cells)
    max_i = max(c[0] for c in cells)
    min_j = min(c[1] for c in cells)
    max_j = max(c[1] for c in cells)
    
    bw = max_i - min_i + 1
    bh = max_j - min_j + 1
    area = len(cells) # if not a perfect rectangle, this shows it
    
    # We redraw each cell
    for (i, j) in cells:
        x_cell = hx + i * unit
        y_cell = hy + j * unit
        # draw colored rectangle
        cv2.rectangle(out, (x_cell, y_cell), (x_cell+unit, y_cell+unit), [int(c) for c in color], -1)
        # draw white border inside the cell to keep the grid look
        cv2.rectangle(out, (x_cell, y_cell), (x_cell+unit, y_cell+unit), (255, 255, 255), 1)

# Add text via PIL
pil_out = Image.fromarray(cv2.cvtColor(out, cv2.COLOR_BGR2RGB))
draw = ImageDraw.Draw(pil_out)

try:
    font = ImageFont.truetype("malgun.ttf", 14)
    font_small = ImageFont.truetype("malgun.ttf", 10)
except:
    font = ImageFont.load_default()
    font_small = font

for cells, color in blocks:
    min_i = min(c[0] for c in cells)
    max_i = max(c[0] for c in cells)
    min_j = min(c[1] for c in cells)
    max_j = max(c[1] for c in cells)
    
    bw = max_i - min_i + 1
    bh = max_j - min_j + 1
    area = len(cells)
    
    # Let's write "w:{} h:{} sq:{}". In a real expo, a unit is usually 3m x 3m (9m^2)
    width_m = bw * 3
    height_m = bh * 3
    area_m = area * 9
    
    # Korean text for dimension
    text1 = f"{width_m}m x {height_m}m"
    text2 = f"{area_m}㎡"
    
    # Top-left and bottom-right in pixels
    px = hx + min_i * unit
    py = hy + min_j * unit
    pw = bw * unit
    ph = bh * unit
    cx = px + pw // 2
    cy = py + ph // 2
    
    bbox1 = draw.textbbox((0, 0), text1, font=font)
    tw1 = bbox1[2] - bbox1[0]
    th1 = bbox1[3] - bbox1[1]
    
    bbox2 = draw.textbbox((0, 0), text2, font=font)
    tw2 = bbox2[2] - bbox2[0]
    th2 = bbox2[3] - bbox2[1]
    
    draw.text((cx - tw1//2, cy - th1 - 2), text1, fill="black", font=font)
    draw.text((cx - tw2//2, cy + 2), text2, fill="black", font=font)

out_cv = cv2.cvtColor(np.array(pil_out), cv2.COLOR_RGB2BGR)

# Draw hall dimension on top of hall
hall_w_m = cols * 3
hall_h_m = rows * 3
hall_area_m = cols * rows * 9
hall_text = f"Exhibition Hall: {hall_w_m}m x {hall_h_m}m ({hall_area_m}㎡) - 1 unit = 3m x 3m"

# put text near top
cv2.putText(out_cv, hall_text, (hx, hy - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)

cv2.imwrite('rebuilt_map.png', out_cv)
print("Saved rebuilt_map.png")
