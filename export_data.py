import cv2
import numpy as np
import json

img = cv2.imread('map.png')
hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
orig_h, orig_w, _ = img.shape

# Dynamically find the grey border
grey_mask = ((hsv[:, :, 1] < 20) & (hsv[:, :, 2] < 200) & (hsv[:, :, 2] > 100)).astype(np.uint8)*255
contours, _ = cv2.findContours(grey_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
largest_cnt = max(contours, key=cv2.contourArea)
hx, hy, hw, hh = cv2.boundingRect(largest_cnt)

unit = int(round(hw / 20)) # 899 / 20 = 45

cols = int(round(hw / unit))
rows = int(round(hh / unit))

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
        
        # Colored booths have saturation > 10
        if mean_hsv[1] > 15 and mean_hsv[2] > 100:
            bgr_color = np.mean(img[cy-2:cy+3, cx-2:cx+3], axis=(0,1)).astype(int)
            bgr_color = tuple(bgr_color)
            
            found_block = None
            for idx, (cells, c) in enumerate(blocks):
                if color_distance(c, bgr_color) < 20: 
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
            else:
                blocks.append((set([(i, j)]), bgr_color))

def merge_blocks(blocks):
    merged = True
    while merged:
        merged = False
        for i in range(len(blocks)):
            for j in range(i+1, len(blocks)):
                if color_distance(blocks[i][1], blocks[j][1]) < 30:
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

booths_data = []

for idx, (cells, color) in enumerate(blocks):
    min_i = min(c[0] for c in cells)
    max_i = max(c[0] for c in cells)
    min_j = min(c[1] for c in cells)
    max_j = max(c[1] for c in cells)
    
    bw = max_i - min_i + 1
    bh = max_j - min_j + 1
    
    # Store color as hex for css
    hex_color = '#%02x%02x%02x' % (color[2], color[1], color[0])
    
    booths_data.append({
        'id': f'booth_{idx}',
        'x': min_i,
        'y': min_j,
        'width': bw,
        'height': bh,
        'color': hex_color,
        'name': '',
        'description': ''
    })

data = {
    'hall': {
        'cols': cols,
        'rows': rows,
        'unitSizePixels': unit, # For calculation
        'unitSizeMeters': 3
    },
    'booths': booths_data
}

with open('booths.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=4, ensure_ascii=False)

print("Exported to booths.json")
