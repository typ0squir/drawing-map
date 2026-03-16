// Constants
const UNIT_PX = 45; // Based on exported data
const UNIT_M = 3;   // Real-world size: 3x3 meters

// State
let booths = [];
let hallStats = null;
let currentMode = 'view'; // 'view' or 'edit'

// Elements
const mapContainer = document.getElementById('mapContainer');
const modeSwitch = document.getElementById('modeSwitch');
const labelView = document.getElementById('label-view');
const labelEdit = document.getElementById('label-edit');
const addBoothBtn = document.getElementById('addBoothBtn');
const downloadBtn = document.getElementById('downloadBtn');
const resetBtn = document.getElementById('resetBtn');

const modal = document.getElementById('infoModal');
const closeBtn = document.querySelector('.close-btn');
const cancelBtn = document.querySelector('.close-modal-btn');
const saveBoothInfoBtn = document.getElementById('saveBoothInfoBtn');
const deleteBoothBtn = document.getElementById('deleteBoothBtn');
const toast = document.getElementById('toast');

const formBoothId = document.getElementById('boothId');
const formBoothName = document.getElementById('boothName');
const formBoothDesc = document.getElementById('boothDesc');
const formBoothColor = document.getElementById('boothColor');
const colorGroup = document.getElementById('colorGroup');
const formBoothSize = document.getElementById('boothSizeDisplay');

// Initialize
function init() {
    // Check localStorage first
    const savedData = localStorage.getItem('boothData');
    if (savedData) {
        const data = JSON.parse(savedData);
        booths = data.booths;
        hallStats = data.hall;
    } else {
        // Fallback to INITIAL_DATA from booths_data.js
        booths = INITIAL_DATA.booths;
        hallStats = INITIAL_DATA.hall;
    }

    // Set map size based on hall cols/rows
    mapContainer.style.width = `${hallStats.cols * UNIT_PX}px`;
    mapContainer.style.height = `${hallStats.rows * UNIT_PX}px`;

    renderMap();
    setupEventListeners();
}

function renderMap() {
    mapContainer.innerHTML = '';
    booths.forEach(booth => {
        const el = document.createElement('div');
        el.className = 'booth';
        el.id = booth.id;

        // Positioning and size using CSS left, top, width, height
        el.style.left = `${booth.x * UNIT_PX}px`;
        el.style.top = `${booth.y * UNIT_PX}px`;
        el.style.width = `${booth.width * UNIT_PX}px`;
        el.style.height = `${booth.height * UNIT_PX}px`;

        el.style.backgroundColor = booth.color;

        // Inner content
        const wM = booth.width * UNIT_M;
        const hM = booth.height * UNIT_M;
        const sqM = booth.width * booth.height * UNIT_M * UNIT_M;

        el.innerHTML = `
            <div class="booth-name">${booth.name || ''}</div>
            <div class="booth-size">${wM}m x ${hM}m</div>
            <div class="resize-handle"></div>
        `;

        mapContainer.appendChild(el);

        // Setup Drag & Drop for exact unit snapping
        setupBoothInteraction(el, booth);
    });
}

function setupEventListeners() {
    // Mode Switch
    modeSwitch.addEventListener('change', (e) => {
        if (e.target.checked) {
            currentMode = 'edit';
            document.body.classList.remove('mode-view');
            document.body.classList.add('mode-edit');
            labelEdit.classList.add('active');
            labelView.classList.remove('active');
            addBoothBtn.style.display = 'inline-block';
        } else {
            currentMode = 'view';
            document.body.classList.add('mode-view');
            document.body.classList.remove('mode-edit');
            labelView.classList.add('active');
            labelEdit.classList.remove('active');
            addBoothBtn.style.display = 'none';
        }
    });

    // Default mode
    document.body.classList.add('mode-view');

    // Controls
    addBoothBtn.addEventListener('click', () => {
        const newId = 'booth_' + Date.now();
        const newBooth = {
            id: newId,
            x: 0,
            y: 0,
            width: 2,
            height: 2,
            color: '#3B82F6',
            name: 'New Booth',
            description: ''
        };
        booths.push(newBooth);
        saveToLocalStorage();
        renderMap();
    });

    resetBtn.addEventListener('click', () => {
        if (confirm('Are you sure you want to reset to original layout? All data will be lost.')) {
            localStorage.removeItem('boothData');
            init();
            showToast('Reset to original layout');
        }
    });

    downloadBtn.addEventListener('click', () => {
        const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify({
            hall: hallStats,
            booths: booths
        }, null, 4));
        const downloadAnchorNode = document.createElement('a');
        downloadAnchorNode.setAttribute("href", dataStr);
        downloadAnchorNode.setAttribute("download", "booths_exported.json");
        document.body.appendChild(downloadAnchorNode); // required for firefox
        downloadAnchorNode.click();
        downloadAnchorNode.remove();
    });

    // Modal
    closeBtn.addEventListener('click', closeModal);
    cancelBtn.addEventListener('click', closeModal);

    saveBoothInfoBtn.addEventListener('click', () => {
        const id = formBoothId.value;
        const index = booths.findIndex(b => b.id === id);
        if (index !== -1) {
            booths[index].name = formBoothName.value;
            booths[index].description = formBoothDesc.value;
            if (currentMode === 'edit') {
                booths[index].color = formBoothColor.value;
            }
            saveToLocalStorage();
            renderMap();
            closeModal();
            showToast('Saved Successfully');
        }
    });

    deleteBoothBtn.addEventListener('click', () => {
        if (confirm('Are you sure you want to delete this booth?')) {
            const id = formBoothId.value;
            booths = booths.filter(b => b.id !== id);
            saveToLocalStorage();
            renderMap();
            closeModal();
            showToast('Booth Deleted');
        }
    });

    // Close modal on outside click
    window.addEventListener('click', (e) => {
        if (e.target == modal) {
            closeModal();
        }
    });
}

function setupBoothInteraction(el, boothInfo) {
    let isDragging = false;
    let isResizing = false;
    let startX, startY, startLeft, startTop, startWidth, startHeight;

    const handle = el.querySelector('.resize-handle');

    // Resize mousedown
    handle.addEventListener('mousedown', (e) => {
        if (currentMode !== 'edit') return;
        e.stopPropagation();
        isResizing = true;
        startX = e.clientX;
        startY = e.clientY;
        startWidth = parseInt(el.style.width, 10);
        startHeight = parseInt(el.style.height, 10);

        document.addEventListener('mousemove', onMouseMove);
        document.addEventListener('mouseup', onMouseUp);
    });

    // Drag mousedown
    el.addEventListener('mousedown', (e) => {
        if (currentMode === 'view') {
            // In View mode, click opens info
            openModal(boothInfo);
            return;
        }

        if (currentMode !== 'edit' || isResizing) return;

        isDragging = true;
        startX = e.clientX;
        startY = e.clientY;
        startLeft = parseInt(el.style.left, 10) || 0;
        startTop = parseInt(el.style.top, 10) || 0;

        // Provide visual feedback
        el.style.zIndex = 1000;
        el.style.opacity = 0.8;

        document.addEventListener('mousemove', onMouseMove);
        document.addEventListener('mouseup', onMouseUp);
    });

    function onMouseMove(e) {
        if (!isDragging && !isResizing) return;

        const dx = e.clientX - startX;
        const dy = e.clientY - startY;

        if (isDragging) {
            let newLeft = startLeft + dx;
            let newTop = startTop + dy;

            // Constrain
            newLeft = Math.max(0, Math.min(newLeft, mapContainer.offsetWidth - el.offsetWidth));
            newTop = Math.max(0, Math.min(newTop, mapContainer.offsetHeight - el.offsetHeight));

            el.style.left = `${newLeft}px`;
            el.style.top = `${newTop}px`;
        }

        if (isResizing) {
            let newWidth = startWidth + dx;
            let newHeight = startHeight + dy;

            // Constrain minimum size (1x1 unit)
            newWidth = Math.max(UNIT_PX, newWidth);
            newHeight = Math.max(UNIT_PX, newHeight);

            // Constrain to container
            const maxW = mapContainer.offsetWidth - parseInt(el.style.left, 10);
            const maxH = mapContainer.offsetHeight - parseInt(el.style.top, 10);
            newWidth = Math.min(newWidth, maxW);
            newHeight = Math.min(newHeight, maxH);

            el.style.width = `${newWidth}px`;
            el.style.height = `${newHeight}px`;
        }
    }

    function onMouseUp(e) {
        if (isDragging) {
            isDragging = false;
            el.style.zIndex = '';
            el.style.opacity = 1;

            // Snap to grid
            const currentLeft = parseInt(el.style.left, 10);
            const currentTop = parseInt(el.style.top, 10);

            const gridX = Math.round(currentLeft / UNIT_PX);
            const gridY = Math.round(currentTop / UNIT_PX);

            boothInfo.x = gridX;
            boothInfo.y = gridY;

            el.style.left = `${gridX * UNIT_PX}px`;
            el.style.top = `${gridY * UNIT_PX}px`;
        }

        if (isResizing) {
            isResizing = false;

            // Snap to grid
            const currentWidth = parseInt(el.style.width, 10);
            const currentHeight = parseInt(el.style.height, 10);

            const gridW = Math.round(currentWidth / UNIT_PX);
            const gridH = Math.round(currentHeight / UNIT_PX);

            boothInfo.width = Math.max(1, gridW);
            boothInfo.height = Math.max(1, gridH);

            el.style.width = `${boothInfo.width * UNIT_PX}px`;
            el.style.height = `${boothInfo.height * UNIT_PX}px`;

            // Update Inner Content
            const wM = boothInfo.width * UNIT_M;
            const hM = boothInfo.height * UNIT_M;
            el.querySelector('.booth-size').textContent = `${wM}m x ${hM}m`;
        }

        document.removeEventListener('mousemove', onMouseMove);
        document.removeEventListener('mouseup', onMouseUp);

        // Save state
        saveToLocalStorage();
    }

    // Also allow Edit Mode click to open modal
    el.addEventListener('click', (e) => {
        // If we didn't drag/resize, and just clicked
        if (currentMode === 'edit' && Math.abs(e.clientX - startX) < 3 && Math.abs(e.clientY - startY) < 3) {
            openModal(boothInfo);
        }
    });
}

function openModal(boothInfo) {
    formBoothId.value = boothInfo.id;
    formBoothName.value = boothInfo.name || '';
    formBoothDesc.value = boothInfo.description || '';

    const wM = boothInfo.width * UNIT_M;
    const hM = boothInfo.height * UNIT_M;
    const sqM = boothInfo.width * boothInfo.height * UNIT_M * UNIT_M;
    formBoothSize.textContent = `${wM}m x ${hM}m (${sqM}㎡)`;

    if (currentMode === 'edit') {
        colorGroup.style.display = 'block';
        formBoothColor.value = rgb2hex(boothInfo.color);
        deleteBoothBtn.style.display = 'block';
    } else {
        colorGroup.style.display = 'none';
        deleteBoothBtn.style.display = 'none';
        // In view mode, if description exists, show it, otherwise show placeholders
    }

    modal.classList.add('show');
}

function closeModal() {
    modal.classList.remove('show');
}

function saveToLocalStorage() {
    const data = {
        hall: hallStats,
        booths: booths
    };
    localStorage.setItem('boothData', JSON.stringify(data));
}

function showToast(msg) {
    toast.textContent = msg;
    toast.classList.add('show');
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

// Utility to convert rgb(,,) to hex if needed 
function rgb2hex(rgb) {
    if (/^#/.test(rgb)) return rgb; // already hex
    rgb = rgb.match(/^rgba?[\s+]?\([\s+]?(\d+)[\s+]?,[\s+]?(\d+)[\s+]?,[\s+]?(\d+)[\s+]?/i);
    return (rgb && rgb.length === 4) ? "#" +
        ("0" + parseInt(rgb[1], 10).toString(16)).slice(-2) +
        ("0" + parseInt(rgb[2], 10).toString(16)).slice(-2) +
        ("0" + parseInt(rgb[3], 10).toString(16)).slice(-2) : '';
}

// Run
window.addEventListener('DOMContentLoaded', init);
