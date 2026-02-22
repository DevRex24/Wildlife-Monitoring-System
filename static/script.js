let lastAlertId = 0;
let systemActive = true;
let selectedFile = null;
let sessionStartTime = new Date();
let totalDetections = 0;
let soundEnabled = true;
let lastThreatState = false;  // Track previous threat state to detect new threats

// Cumulative detection counts for the session
let cumulativeCounts = {
    person: 0,
    car: 0,
    truck: 0,
    motorcycle: 0,
    bus: 0,
    bicycle: 0,
    animal: 0,
    other: 0,
    total: 0
};

// Track last detection state to avoid double counting
let lastDetectionSignature = '';

// ============ LIVE TIME TRACKING ============

function updateLiveTime() {
    const now = new Date();
    
    // Format time as HH:MM:SS
    const timeStr = now.toLocaleTimeString('en-US', { 
        hour12: false, 
        hour: '2-digit', 
        minute: '2-digit', 
        second: '2-digit' 
    });
    
    // Format date
    const dateStr = now.toLocaleDateString('en-US', { 
        weekday: 'short',
        year: 'numeric', 
        month: 'short', 
        day: 'numeric' 
    });
    
    // Update header time display
    const currentTimeEl = document.getElementById('currentTime');
    const currentDateEl = document.getElementById('currentDate');
    if (currentTimeEl) currentTimeEl.textContent = timeStr;
    if (currentDateEl) currentDateEl.textContent = dateStr;
    
    // Update live stats bar
    const liveTimeEl = document.getElementById('liveTime');
    const liveDateEl = document.getElementById('liveDate');
    if (liveTimeEl) liveTimeEl.textContent = timeStr;
    if (liveDateEl) liveDateEl.textContent = now.toLocaleDateString('en-GB');
    
    // Update session time
    updateSessionTime();
    
    // Update system uptime
    updateSystemUptime();
}

function updateSessionTime() {
    const now = new Date();
    const diff = now - sessionStartTime;
    
    const hours = Math.floor(diff / 3600000);
    const minutes = Math.floor((diff % 3600000) / 60000);
    const seconds = Math.floor((diff % 60000) / 1000);
    
    const sessionStr = `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
    
    const sessionTimeEl = document.getElementById('sessionTime');
    if (sessionTimeEl) sessionTimeEl.textContent = sessionStr;
}

function updateSystemUptime() {
    const now = new Date();
    const diff = now - sessionStartTime;
    
    const hours = Math.floor(diff / 3600000);
    const minutes = Math.floor((diff % 3600000) / 60000);
    const seconds = Math.floor((diff % 60000) / 1000);
    
    const uptimeStr = `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
    
    const uptimeEl = document.getElementById('systemUptime');
    if (uptimeEl) uptimeEl.textContent = uptimeStr;
}

function updateDetectionCount(count) {
    totalDetections = count;
    const detectionCountEl = document.getElementById('detectionCount');
    if (detectionCountEl) detectionCountEl.textContent = totalDetections;
}

// Start live time updates
setInterval(updateLiveTime, 1000);
updateLiveTime(); // Initial update

// Tab Switching
function switchTab(tab) {
    const liveTab = document.getElementById('liveTab');
    const uploadTab = document.getElementById('uploadTab');
    const galleryTab = document.getElementById('galleryTab');
    const recordingsTab = document.getElementById('recordingsTab');
    const statsTab = document.getElementById('statsTab');
    const livePanel = document.getElementById('livePanel');
    const uploadPanel = document.getElementById('uploadPanel');
    const galleryPanel = document.getElementById('galleryPanel');
    const recordingsPanel = document.getElementById('recordingsPanel');
    const statsPanel = document.getElementById('statsPanel');
    
    // Remove active from all tabs
    liveTab.classList.remove('active');
    uploadTab.classList.remove('active');
    if (galleryTab) galleryTab.classList.remove('active');
    recordingsTab.classList.remove('active');
    if (statsTab) statsTab.classList.remove('active');
    
    // Hide all panels
    livePanel.style.display = 'none';
    uploadPanel.style.display = 'none';
    if (galleryPanel) galleryPanel.style.display = 'none';
    recordingsPanel.style.display = 'none';
    if (statsPanel) statsPanel.style.display = 'none';
    
    if (tab === 'live') {
        liveTab.classList.add('active');
        livePanel.style.display = 'flex';
    } else if (tab === 'upload') {
        uploadTab.classList.add('active');
        uploadPanel.style.display = 'flex';
    } else if (tab === 'gallery') {
        galleryTab.classList.add('active');
        galleryPanel.style.display = 'flex';
        loadGallery();
    } else if (tab === 'recordings') {
        recordingsTab.classList.add('active');
        recordingsPanel.style.display = 'flex';
        loadRecordings();
    } else if (tab === 'stats') {
        statsTab.classList.add('active');
        statsPanel.style.display = 'flex';
        loadStatistics();
    }
}

// System Toggle
function toggleSystem() {
    fetch('/toggle_system', { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                systemActive = data.system_active;
                updateToggleButton();
            }
        })
        .catch(err => console.error('Toggle failed:', err));
}

function updateToggleButton() {
    const btn = document.getElementById('toggleBtn');
    const toggleText = document.getElementById('toggleText');
    const threatBanner = document.getElementById('threatBanner');
    
    if (systemActive) {
        btn.classList.add('active');
        btn.classList.remove('inactive');
        toggleText.textContent = 'System ON';
    } else {
        btn.classList.remove('active');
        btn.classList.add('inactive');
        toggleText.textContent = 'System OFF';
        threatBanner.classList.add('hidden');
    }
}

// Check system status and update detections display
function checkSystemStatus() {
    fetch('/current_status')
        .then(res => res.json())
        .then(data => {
            if (data.system_active !== undefined && data.system_active !== systemActive) {
                systemActive = data.system_active;
                updateToggleButton();
            }
            
            // Update threat banner with severity
            const threatBanner = document.getElementById('threatBanner');
            const isThreatActive = data.threat_active && systemActive;
            
            if (isThreatActive) {
                threatBanner.classList.remove('hidden');
                
                // Update threat banner with severity info
                updateThreatBanner(data.severity);
                
                // Play sound when NEW threat is detected (not already active)
                if (!lastThreatState && soundEnabled) {
                    console.log('🚨 New threat detected - playing alarm!');
                    playAlertSound();
                }
            } else {
                threatBanner.classList.add('hidden');
            }
            
            // Update last threat state
            lastThreatState = isThreatActive;
            
            // Update detected objects with severity
            updateDetectedObjects(data.detections || [], data.severity);
        })
        .catch(err => console.error('Status check failed:', err));
}

// Update threat banner with severity level
function updateThreatBanner(severity) {
    const threatBanner = document.getElementById('threatBanner');
    const threatText = threatBanner.querySelector('.threat-text');
    
    if (!severity) return;
    
    // Update banner color based on severity
    threatBanner.className = 'threat-banner';
    threatBanner.classList.add(`severity-${severity.level.toLowerCase()}`);
    
    // Update text
    if (threatText) {
        threatText.textContent = `${severity.level} ALERT - ${severity.person_count || 0} Person(s), ${severity.vehicle_count || 0} Vehicle(s)`;
    }
}

// Update detected objects display
function updateDetectedObjects(detections, severity) {
    const objectsList = document.getElementById('objectsList');
    
    // Update live counts
    updateLiveCounts(detections);
    
    if (!detections || detections.length === 0) {
        objectsList.innerHTML = '<p class="no-detection">No objects detected</p>';
        updateDetectionStatus(false);
        return;
    }
    
    // Update detection status
    updateDetectionStatus(true, severity);
    
    // Group by class and count
    const grouped = {};
    const counts = {};
    detections.forEach(det => {
        if (!grouped[det.class] || grouped[det.class] < det.confidence) {
            grouped[det.class] = det.confidence;
        }
        counts[det.class] = (counts[det.class] || 0) + 1;
    });
    
    // Severity badge HTML
    let severityBadge = '';
    if (severity && severity.level !== 'NONE') {
        const severityColors = {
            'CRITICAL': '#ff0000',
            'HIGH': '#da3633',
            'MEDIUM': '#f0883e',
            'LOW': '#58a6ff'
        };
        severityBadge = `
            <div class="severity-indicator" style="background: ${severityColors[severity.level] || '#8b949e'}; padding: 8px 12px; border-radius: 6px; margin-bottom: 12px; text-align: center;">
                <span style="font-weight: 600; color: white;">
                    ${severity.level === 'CRITICAL' ? '🔴' : severity.level === 'HIGH' ? '🟠' : severity.level === 'MEDIUM' ? '🟡' : '🔵'} 
                    ${severity.level} THREAT LEVEL
                </span>
                <span style="color: rgba(255,255,255,0.8); font-size: 0.85em; display: block; margin-top: 4px;">
                    Score: ${severity.score}/100 | ${severity.total_count || detections.length} threat(s)
                </span>
            </div>
        `;
    }
    
    // Animal classes for icon selection
    const animalClasses = ['bird', 'cat', 'dog', 'horse', 'sheep', 'cow', 'elephant', 'bear', 'zebra', 'giraffe'];
    const vehicleClasses = ['car', 'truck', 'bus', 'motorcycle', 'bicycle'];
    
    // Get appropriate icon for detection class
    function getDetectionIcon(className) {
        const lowerClass = className.toLowerCase();
        if (lowerClass === 'person') return '👤';
        if (animalClasses.includes(lowerClass)) return '🐾';
        if (vehicleClasses.includes(lowerClass)) return '🚗';
        return '📦';
    }
    
    // Get bar fill class
    function getBarClass(className) {
        const lowerClass = className.toLowerCase();
        if (lowerClass === 'person') return 'person';
        if (animalClasses.includes(lowerClass)) return 'animal';
        return 'vehicle';
    }
    
    let html = severityBadge;
    for (const [className, confidence] of Object.entries(grouped)) {
        const icon = getDetectionIcon(className);
        const count = counts[className];
        const percent = Math.round(confidence * 100);
        const barClass = getBarClass(className);
        html += `
            <div class="object-item">
                <span class="object-icon">${icon}</span>
                <span class="object-name">${className} ${count > 1 ? `<span class="object-count">(×${count})</span>` : ''}</span>
                <div class="object-bar">
                    <div class="object-bar-fill ${barClass}" style="width: ${percent}%"></div>
                </div>
                <span class="object-confidence">${percent}%</span>
            </div>
        `;
    }
    objectsList.innerHTML = html;
}

// Update live counts display
function updateLiveCounts(detections) {
    // Current frame counts
    const currentCounts = {
        person: 0,
        car: 0,
        truck: 0,
        motorcycle: 0,
        bus: 0,
        bicycle: 0,
        animal: 0,
        other: 0
    };
    
    // Animal classes from COCO dataset
    const animalClasses = ['bird', 'cat', 'dog', 'horse', 'sheep', 'cow', 'elephant', 'bear', 'zebra', 'giraffe'];
    
    // Count detections by type in current frame
    if (detections && detections.length > 0) {
        detections.forEach(det => {
            const className = det.class.toLowerCase();
            
            if (className === 'person') {
                currentCounts.person++;
            } else if (className === 'car') {
                currentCounts.car++;
            } else if (className === 'truck') {
                currentCounts.truck++;
            } else if (className === 'motorcycle' || className === 'motorbike') {
                currentCounts.motorcycle++;
            } else if (className === 'bus') {
                currentCounts.bus++;
            } else if (className === 'bicycle' || className === 'bike') {
                currentCounts.bicycle++;
            } else if (animalClasses.includes(className)) {
                currentCounts.animal++;
            } else {
                currentCounts.other++;
            }
        });
    }
    
    // Create a signature of current detections to track changes
    const currentSignature = JSON.stringify(currentCounts);
    
    // Only add to cumulative if detections changed (new detection event)
    if (currentSignature !== lastDetectionSignature && detections && detections.length > 0) {
        // Add current counts to cumulative
        cumulativeCounts.person += currentCounts.person;
        cumulativeCounts.car += currentCounts.car;
        cumulativeCounts.truck += currentCounts.truck;
        cumulativeCounts.motorcycle += currentCounts.motorcycle;
        cumulativeCounts.bus += currentCounts.bus;
        cumulativeCounts.bicycle += currentCounts.bicycle;
        cumulativeCounts.animal += currentCounts.animal;
        cumulativeCounts.other += currentCounts.other;
        
        // Update total
        const frameTotal = Object.values(currentCounts).reduce((sum, val) => sum + val, 0);
        cumulativeCounts.total += frameTotal;
        
        lastDetectionSignature = currentSignature;
    }
    
    // Update DOM elements with CUMULATIVE counts
    const personEl = document.getElementById('livePersonCount');
    const carEl = document.getElementById('liveCarCount');
    const truckEl = document.getElementById('liveTruckCount');
    const motorcycleEl = document.getElementById('liveMotorcycleCount');
    const busEl = document.getElementById('liveBusCount');
    const bicycleEl = document.getElementById('liveBicycleCount');
    const animalEl = document.getElementById('liveAnimalCount');
    const otherEl = document.getElementById('liveOtherCount');
    const totalEl = document.getElementById('liveTotalCount');
    
    if (personEl) personEl.textContent = cumulativeCounts.person;
    if (carEl) carEl.textContent = cumulativeCounts.car;
    if (truckEl) truckEl.textContent = cumulativeCounts.truck;
    if (motorcycleEl) motorcycleEl.textContent = cumulativeCounts.motorcycle;
    if (busEl) busEl.textContent = cumulativeCounts.bus;
    if (bicycleEl) bicycleEl.textContent = cumulativeCounts.bicycle;
    if (animalEl) animalEl.textContent = cumulativeCounts.animal;
    if (otherEl) otherEl.textContent = cumulativeCounts.other;
    if (totalEl) totalEl.textContent = cumulativeCounts.total;
    
    // Update card active states based on CURRENT detections (for highlighting)
    updateCountCardStates(currentCounts);
}

// Update count card active states
function updateCountCardStates(counts) {
    const cards = {
        person: document.querySelector('.count-card.person'),
        car: document.querySelector('.count-card.car'),
        truck: document.querySelector('.count-card.truck'),
        motorcycle: document.querySelector('.count-card.motorcycle'),
        bus: document.querySelector('.count-card.bus'),
        bicycle: document.querySelector('.count-card.bicycle'),
        animal: document.querySelector('.count-card.animal'),
        other: document.querySelector('.count-card.other')
    };
    
    for (const [type, card] of Object.entries(cards)) {
        if (card) {
            if (counts[type] > 0) {
                card.classList.add('active');
            } else {
                card.classList.remove('active');
            }
        }
    }
}

// Update detection status indicator
function updateDetectionStatus(hasThreat, severity) {
    const statusEl = document.getElementById('detectionStatus');
    if (!statusEl) return;
    
    const statusDot = statusEl.querySelector('.status-dot');
    const statusText = statusEl.querySelector('.status-text');
    
    if (hasThreat) {
        statusDot.className = 'status-dot threat';
        if (severity && severity.level) {
            statusText.textContent = `${severity.level} Alert Active`;
        } else {
            statusText.textContent = 'Threat Detected';
        }
    } else {
        statusDot.className = 'status-dot safe';
        statusText.textContent = 'No Active Threats';
    }
}

// Update alerts list
function updateAlerts() {
    fetch('/alerts?limit=10')
        .then(res => res.json())
        .then(data => {
            // Update detection count in the stats bar
            if (data.total_count !== undefined) {
                updateDetectionCount(data.total_count);
            } else if (data.alerts) {
                updateDetectionCount(data.alerts.length);
            }
            
            if (data.success && data.alerts.length > 0) {
                const alertsList = document.getElementById('alertsList');
                const threatsList = document.getElementById('threatsList');
                
                let alertsHtml = '';
                let threatsHtml = '';
                
                data.alerts.forEach(alert => {
                    const exactTime = formatExactTime(new Date(alert.timestamp));
                    // Normalize path: replace backslashes with forward slashes
                    const imagePath = (alert.image_path || '').replace(/\\/g, '/');
                    const detectionTypes = alert.detection_type.split(',').map(t => t.trim());
                    
                    const titleHtml = detectionTypes.map(t => 
                        `<span>${t === 'person' ? 'Human' : t.charAt(0).toUpperCase() + t.slice(1)} Detected</span>`
                    ).join(' and ');
                    
                    const itemHtml = `
                        <div class="alert-item">
                            <img src="/${imagePath}" alt="Alert" class="alert-thumbnail" onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 60 45%22><rect fill=%22%23161b22%22 width=%2260%22 height=%2245%22/><text x=%2230%22 y=%2225%22 fill=%22%238b949e%22 text-anchor=%22middle%22 font-size=%2210%22>No img</text></svg>'">
                            <div class="alert-info">
                                <div class="alert-title">${titleHtml}</div>
                                <div class="alert-path">${imagePath.split('/').pop() || 'snapshot.jpg'}</div>
                            </div>
                            <div class="alert-time">${exactTime}</div>
                            <button class="alert-view-btn" onclick="viewAlert('${imagePath}')">View</button>
                        </div>
                    `;
                    
                    alertsHtml += itemHtml;
                    threatsHtml += itemHtml;

                    if (alert.id > lastAlertId) {
                        showAlertNotification(alert);
                        lastAlertId = alert.id;
                    }
                });
                
                alertsList.innerHTML = alertsHtml;
                threatsList.innerHTML = threatsHtml;
            }
        });
}

// Format exact time for alerts
function formatExactTime(date) {
    const today = new Date();
    const isToday = date.toDateString() === today.toDateString();
    
    const timeStr = date.toLocaleTimeString('en-US', { 
        hour: '2-digit', 
        minute: '2-digit',
        second: '2-digit',
        hour12: true 
    });
    
    if (isToday) {
        return `Today at ${timeStr}`;
    } else {
        const dateStr = date.toLocaleDateString('en-US', { 
            month: 'short', 
            day: 'numeric',
            year: 'numeric'
        });
        return `${dateStr} at ${timeStr}`;
    }
}

// View alert image
function viewAlert(imagePath) {
    if (imagePath) {
        // Normalize path: replace backslashes with forward slashes
        const normalizedPath = imagePath.replace(/\\/g, '/');
        window.open('/' + normalizedPath, '_blank');
    }
}

// Show notification popup
function showAlertNotification(alert) {
    const notification = document.getElementById('alertNotification');
    const message = document.getElementById('alertMessage');
    
    // Format detection type nicely
    const detectionTypes = alert.detection_type.split(',').map(t => {
        const type = t.trim().toLowerCase();
        if (type === 'person') return '👤 Human Intruder';
        if (type === 'car') return '🚗 Vehicle (Car)';
        if (type === 'truck') return '🚛 Vehicle (Truck)';
        if (type === 'motorcycle') return '🏍️ Motorcycle';
        if (type === 'bus') return '🚌 Vehicle (Bus)';
        return `⚠️ ${type.charAt(0).toUpperCase() + type.slice(1)}`;
    });
    
    const confidence = alert.confidence ? ` (${Math.round(alert.confidence * 100)}% confidence)` : '';
    const time = new Date(alert.timestamp).toLocaleTimeString('en-US', { 
        hour: '2-digit', 
        minute: '2-digit',
        second: '2-digit',
        hour12: true 
    });
    
    // Extract severity from notes if available
    const severityMatch = alert.notes?.match(/\[(LOW|MEDIUM|HIGH|CRITICAL)\]/);
    const severityLevel = severityMatch ? severityMatch[1] : 'MEDIUM';
    const severityColors = {
        'CRITICAL': '#ff0000',
        'HIGH': '#da3633',
        'MEDIUM': '#f0883e',
        'LOW': '#58a6ff'
    };
    const severityEmoji = {
        'CRITICAL': '🔴',
        'HIGH': '🟠',
        'MEDIUM': '🟡',
        'LOW': '🔵'
    };
    
    // Update notification color based on severity
    notification.style.background = `linear-gradient(135deg, ${severityColors[severityLevel]} 0%, ${severityColors[severityLevel]}dd 100%)`;
    
    message.innerHTML = `
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
            <span style="font-size: 1.5em;">${severityEmoji[severityLevel]}</span>
            <span style="background: rgba(0,0,0,0.3); padding: 4px 12px; border-radius: 20px; font-weight: 600; font-size: 0.85em;">
                ${severityLevel} PRIORITY
            </span>
        </div>
        <div style="font-size: 1.1em; margin-bottom: 8px;">
            <strong>${detectionTypes.join(' & ')}</strong>${confidence}
        </div>
        <div style="font-size: 0.9em; color: rgba(255,255,255,0.9);">
            🚨 Detected in wildlife protection zone at ${time}
        </div>
        <div style="font-size: 0.85em; color: rgba(255,255,255,0.7); margin-top: 5px;">
            Alert ID: #${alert.id} | Camera: ${alert.notes?.match(/\[CAM_\d+\]/)?.[0] || 'CAM_001'}
        </div>
    `;
    
    notification.classList.remove('hidden');
    
    // Play alert sound if enabled
    if (soundEnabled) {
        playAlertSound();
    }
    
    setTimeout(() => notification.classList.add('hidden'), 6000);
}

// Legacy showNotification for backward compatibility
function showNotification(type) {
    // Create a simple alert object for the legacy function
    showAlertNotification({
        detection_type: type,
        timestamp: new Date().toISOString(),
        id: lastAlertId,
        confidence: null,
        notes: ''
    });
}

// ============ SOUND ALARM FEATURE ============

// Create audio context for generating alert sounds
let audioContext = null;

function initAudioContext() {
    if (!audioContext) {
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
    }
    return audioContext;
}

function playAlertSound() {
    if (!soundEnabled) {
        console.log('🔇 Sound is disabled');
        return;
    }
    
    try {
        const ctx = initAudioContext();
        
        // Resume audio context if it was suspended (browser autoplay policy)
        if (ctx.state === 'suspended') {
            ctx.resume().then(() => {
                console.log('🔊 Audio context resumed');
                createAlertBeeps(ctx);
            });
        } else {
            createAlertBeeps(ctx);
        }
    } catch (err) {
        console.error('Audio play failed:', err);
    }
}

function createAlertBeeps(ctx) {
    const currentTime = ctx.currentTime;
    
    // Create a louder, more attention-grabbing alarm pattern (5 beeps)
    for (let i = 0; i < 5; i++) {
        const oscillator = ctx.createOscillator();
        const gainNode = ctx.createGain();
        
        oscillator.connect(gainNode);
        gainNode.connect(ctx.destination);
        
        // Alarm tone frequency (alternating between two tones for urgency)
        oscillator.frequency.value = i % 2 === 0 ? 880 : 660;
        oscillator.type = 'square';
        
        // Volume envelope - LOUDER (0.5 instead of 0.3)
        gainNode.gain.setValueAtTime(0.5, currentTime + i * 0.2);
        gainNode.gain.exponentialRampToValueAtTime(0.01, currentTime + i * 0.2 + 0.15);
        
        oscillator.start(currentTime + i * 0.2);
        oscillator.stop(currentTime + i * 0.2 + 0.15);
    }
    
    console.log('🔊 Alert sound played!');
}

// Test sound function (for manual testing)
function testAlertSound() {
    playAlertSound();
}

function toggleSound() {
    soundEnabled = !soundEnabled;
    updateSoundButton();
    
    // Initialize audio context on user interaction
    initAudioContext();
    
    // Play test beep when enabling sound
    if (soundEnabled) {
        playAlertSound();
    }
    
    // Save preference to localStorage
    localStorage.setItem('soundEnabled', soundEnabled);
}

function updateSoundButton() {
    const btn = document.getElementById('soundToggleBtn');
    const icon = document.getElementById('soundIcon');
    const text = document.getElementById('soundText');
    
    if (soundEnabled) {
        btn.classList.add('active');
        btn.classList.remove('inactive');
        icon.textContent = '🔊';
        text.textContent = 'Sound ON';
    } else {
        btn.classList.remove('active');
        btn.classList.add('inactive');
        icon.textContent = '🔇';
        text.textContent = 'Sound OFF';
    }
}

// Load sound preference from localStorage
function loadSoundPreference() {
    const saved = localStorage.getItem('soundEnabled');
    if (saved !== null) {
        soundEnabled = saved === 'true';
        updateSoundButton();
    }
}

// Initialize audio context on any user interaction (required by browsers)
function initAudioOnInteraction() {
    if (!audioContext) {
        initAudioContext();
        console.log('🔊 Audio context initialized');
    }
    // Remove listeners after first interaction
    document.removeEventListener('click', initAudioOnInteraction);
    document.removeEventListener('keydown', initAudioOnInteraction);
    document.removeEventListener('touchstart', initAudioOnInteraction);
}

// Add listeners for user interaction to enable audio
document.addEventListener('click', initAudioOnInteraction);
document.addEventListener('keydown', initAudioOnInteraction);
document.addEventListener('touchstart', initAudioOnInteraction);

// Initialize sound preference on page load
loadSoundPreference();

// Initialize audio context on first user interaction (required by browsers)
document.addEventListener('click', function initAudio() {
    initAudioContext();
    document.removeEventListener('click', initAudio);
}, { once: true });

// Image Upload Handling
const imageInput = document.getElementById('imageInput');
const uploadArea = document.getElementById('uploadArea');
const imagePreview = document.getElementById('imagePreview');
const previewImg = document.getElementById('previewImg');
const uploadResult = document.getElementById('uploadResult');

imageInput.addEventListener('change', function(e) {
    const file = e.target.files[0];
    if (file) {
        selectedFile = file;
        const reader = new FileReader();
        reader.onload = function(e) {
            previewImg.src = e.target.result;
            uploadArea.style.display = 'none';
            imagePreview.classList.remove('hidden');
            uploadResult.classList.add('hidden');
        };
        reader.readAsDataURL(file);
    }
});

// Drag and drop
uploadArea.addEventListener('dragover', function(e) {
    e.preventDefault();
    uploadArea.classList.add('drag-over');
});

uploadArea.addEventListener('dragleave', function(e) {
    e.preventDefault();
    uploadArea.classList.remove('drag-over');
});

uploadArea.addEventListener('drop', function(e) {
    e.preventDefault();
    uploadArea.classList.remove('drag-over');
    
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith('image/')) {
        selectedFile = file;
        const reader = new FileReader();
        reader.onload = function(e) {
            previewImg.src = e.target.result;
            uploadArea.style.display = 'none';
            imagePreview.classList.remove('hidden');
            uploadResult.classList.add('hidden');
        };
        reader.readAsDataURL(file);
    }
});

// Analyze uploaded image
async function analyzeImage() {
    if (!selectedFile) return;
    
    const formData = new FormData();
    formData.append('image', selectedFile);
    
    try {
        const res = await fetch('/upload', { method: 'POST', body: formData });
        const data = await res.json();
        
        uploadResult.classList.remove('hidden');
        
        if (data.success) {
            uploadResult.textContent = data.message;
            uploadResult.className = 'upload-result ' + (data.threat_detected ? 'success' : '');
            if (data.threat_detected) {
                updateAlerts();
            }
        } else {
            uploadResult.textContent = 'Error: ' + data.error;
            uploadResult.className = 'upload-result error';
        }
    } catch (err) {
        uploadResult.classList.remove('hidden');
        uploadResult.textContent = 'Upload failed';
        uploadResult.className = 'upload-result error';
    }
    
    // Reset for new upload
    setTimeout(() => {
        uploadArea.style.display = 'block';
        imagePreview.classList.add('hidden');
        selectedFile = null;
    }, 3000);
}

// ============ VIDEO RECORDINGS ============

function loadRecordings() {
    fetch('/recordings')
        .then(res => res.json())
        .then(data => {
            const recordingsList = document.getElementById('recordingsList');
            
            if (data.success && data.recordings.length > 0) {
                let html = '';
                data.recordings.forEach(rec => {
                    const detectionLabel = rec.detection_type === 'person' ? 'Human' : 
                                          rec.detection_type.charAt(0).toUpperCase() + rec.detection_type.slice(1);
                    const cameraId = rec.camera_id || 'CAM_001';
                    
                    html += `
                        <div class="recording-item">
                            <div class="recording-icon">🎬</div>
                            <div class="recording-info">
                                <div class="recording-title">${detectionLabel} Detected</div>
                                <div class="recording-details">${rec.date} at ${rec.time}</div>
                                <div class="recording-camera">📹 ${cameraId}</div>
                                <div class="recording-filename">${rec.filename}</div>
                            </div>
                            <button class="play-btn" onclick="playRecording('${rec.path}')">
                                ▶ Play
                            </button>
                            <a class="download-btn" href="/${rec.path}" download="${rec.filename}">
                                ⬇ Download
                            </a>
                        </div>
                    `;
                });
                recordingsList.innerHTML = html;
            } else {
                recordingsList.innerHTML = '<p class="no-recordings">No recordings yet. Videos are automatically recorded when threats are detected.</p>';
            }
        })
        .catch(err => {
            console.error('Failed to load recordings:', err);
            document.getElementById('recordingsList').innerHTML = '<p class="no-recordings">Failed to load recordings</p>';
        });
}

function playRecording(videoPath) {
    const container = document.getElementById('videoPlayerContainer');
    const video = document.getElementById('videoPlayer');
    
    video.src = '/' + videoPath;
    container.classList.remove('hidden');
    video.play();
}

function closeVideoPlayer() {
    const container = document.getElementById('videoPlayerContainer');
    const video = document.getElementById('videoPlayer');
    
    video.pause();
    video.src = '';
    container.classList.add('hidden');
}

// ============ STATISTICS DASHBOARD ============

let trendChart = null;
let typeChart = null;
let hourlyChart = null;
let weeklyChart = null;

const chartColors = {
    primary: '#58a6ff',
    secondary: '#238636',
    warning: '#d29922',
    danger: '#f85149',
    purple: '#a371f7',
    gray: '#8b949e'
};

function loadStatistics() {
    // Load summary stats
    fetch('/stats')
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                document.getElementById('totalDetections').textContent = data.stats.total_alerts || 0;
                document.getElementById('todayDetections').textContent = data.stats.today_alerts || 0;
                document.getElementById('weekDetections').textContent = data.stats.week_alerts || 0;
                document.getElementById('emailRate').textContent = (data.stats.email_success_rate || 0) + '%';
            }
        });
    
    // Load chart data
    updateCharts();
}

function updateCharts() {
    const timeRange = document.getElementById('timeRangeSelect')?.value || 'daily';
    
    fetch(`/stats/charts?range=${timeRange}`)
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                renderTrendChart(data.data.trend);
                renderTypeChart(data.data.types);
                renderHourlyChart(data.data.hourly);
                renderWeeklyChart(data.data.weekly);
            }
        })
        .catch(err => console.error('Failed to load chart data:', err));
}

function renderTrendChart(data) {
    const ctx = document.getElementById('trendChart')?.getContext('2d');
    if (!ctx) return;
    
    if (trendChart) trendChart.destroy();
    
    trendChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.labels,
            datasets: [{
                label: 'Detections',
                data: data.values,
                borderColor: chartColors.primary,
                backgroundColor: 'rgba(88, 166, 255, 0.1)',
                fill: true,
                tension: 0.4,
                pointBackgroundColor: chartColors.primary,
                pointBorderColor: '#fff',
                pointBorderWidth: 2,
                pointRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: { color: '#8b949e' },
                    grid: { color: 'rgba(139, 148, 158, 0.1)' }
                },
                x: {
                    ticks: { color: '#8b949e' },
                    grid: { display: false }
                }
            }
        }
    });
}

function renderTypeChart(data) {
    const ctx = document.getElementById('typeChart')?.getContext('2d');
    if (!ctx) return;
    
    if (typeChart) typeChart.destroy();
    
    const colors = [chartColors.danger, chartColors.warning, chartColors.purple, chartColors.secondary];
    
    typeChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: data.labels.map(l => l.charAt(0).toUpperCase() + l.slice(1)),
            datasets: [{
                data: data.values,
                backgroundColor: colors.slice(0, data.labels.length),
                borderColor: '#161b22',
                borderWidth: 3
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: { color: '#c9d1d9', padding: 15 }
                }
            }
        }
    });
}

function renderHourlyChart(data) {
    const ctx = document.getElementById('hourlyChart')?.getContext('2d');
    if (!ctx) return;
    
    if (hourlyChart) hourlyChart.destroy();
    
    hourlyChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.labels,
            datasets: [{
                label: 'Detections',
                data: data.values,
                backgroundColor: chartColors.secondary,
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: { color: '#8b949e' },
                    grid: { color: 'rgba(139, 148, 158, 0.1)' }
                },
                x: {
                    ticks: { 
                        color: '#8b949e',
                        maxRotation: 45,
                        callback: function(val, index) {
                            return index % 3 === 0 ? this.getLabelForValue(val) : '';
                        }
                    },
                    grid: { display: false }
                }
            }
        }
    });
}

function renderWeeklyChart(data) {
    const ctx = document.getElementById('weeklyChart')?.getContext('2d');
    if (!ctx) return;
    
    if (weeklyChart) weeklyChart.destroy();
    
    weeklyChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.labels,
            datasets: [
                {
                    label: 'This Week',
                    data: data.thisWeek,
                    backgroundColor: chartColors.primary,
                    borderRadius: 4
                },
                {
                    label: 'Last Week',
                    data: data.lastWeek,
                    backgroundColor: chartColors.gray,
                    borderRadius: 4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: { color: '#c9d1d9' }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: { color: '#8b949e' },
                    grid: { color: 'rgba(139, 148, 158, 0.1)' }
                },
                x: {
                    ticks: { color: '#8b949e' },
                    grid: { display: false }
                }
            }
        }
    });
}

// ============ MULTI-CAMERA SUPPORT ============

let cameraList = [];

function loadCameras() {
    fetch('/cameras')
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                cameraList = data.cameras;
                renderCameraGrid();
                updateCameraCount(data.total);
            }
        })
        .catch(err => {
            console.error('Failed to load cameras:', err);
            // Fallback: show single default camera
            renderDefaultCamera();
        });
}

function renderCameraGrid() {
    const grid = document.getElementById('cameraGrid');
    if (!grid) return;
    
    grid.innerHTML = '';
    
    if (cameraList.length === 0) {
        renderDefaultCamera();
        return;
    }
    
    // Add class for single camera layout
    if (cameraList.length === 1) {
        grid.classList.add('single-camera');
    } else {
        grid.classList.remove('single-camera');
    }
    
    cameraList.forEach(camera => {
        const card = createCameraCard(camera);
        grid.appendChild(card);
    });
}

function createCameraCard(camera) {
    const card = document.createElement('div');
    card.className = 'camera-card';
    card.id = `camera-${camera.id}`;
    
    if (camera.threat) {
        card.classList.add('threat-active');
    }
    
    card.innerHTML = `
        <div class="camera-card-header">
            <div class="camera-info">
                <span class="camera-name">${camera.name}</span>
                <span class="camera-id">${camera.id}</span>
            </div>
            <div class="camera-status">
                <span class="camera-status-dot ${camera.active ? '' : 'offline'}"></span>
                <span style="color: ${camera.active ? '#238636' : '#da3633'}; font-size: 0.8em;">
                    ${camera.active ? 'LIVE' : 'OFFLINE'}
                </span>
            </div>
            <div class="camera-actions">
                <button class="camera-action-btn" onclick="toggleFullscreen('${camera.id}')" title="Fullscreen">⛶</button>
                <button class="camera-action-btn remove" onclick="removeCamera('${camera.id}')" title="Remove">✕</button>
            </div>
        </div>
        <div class="camera-feed">
            <img src="/video_feed/${camera.id}" alt="${camera.name}" onerror="this.src='/static/camera-offline.png'">
            <div class="camera-overlay">
                <span class="camera-tag">${camera.id}</span>
                ${camera.threat ? '<span class="camera-tag threat">⚠ THREAT</span>' : ''}
            </div>
        </div>
    `;
    
    return card;
}

function renderDefaultCamera() {
    const grid = document.getElementById('cameraGrid');
    if (!grid) return;
    
    grid.classList.add('single-camera');
    grid.innerHTML = `
        <div class="camera-card" id="camera-default">
            <div class="camera-card-header">
                <div class="camera-info">
                    <span class="camera-name">Main Camera</span>
                    <span class="camera-id">CAM_001</span>
                </div>
                <div class="camera-status">
                    <span class="camera-status-dot"></span>
                    <span style="color: #238636; font-size: 0.8em;">LIVE</span>
                </div>
                <div class="camera-actions">
                    <button class="camera-action-btn" onclick="toggleFullscreen('default')" title="Fullscreen">⛶</button>
                </div>
            </div>
            <div class="camera-feed">
                <img src="/video_feed" alt="Main Camera">
                <div class="camera-overlay">
                    <span class="camera-tag">CAM_001</span>
                </div>
            </div>
        </div>
    `;
}

function updateCameraCount(count) {
    const countEl = document.getElementById('cameraCount');
    if (countEl) countEl.textContent = count;
}

function showAddCameraModal() {
    const modal = document.getElementById('addCameraModal');
    if (modal) {
        modal.classList.remove('hidden');
        // Clear form
        document.getElementById('cameraName').value = '';
        document.getElementById('cameraSource').value = '';
        document.getElementById('cameraId').value = '';
    }
}

function hideAddCameraModal() {
    const modal = document.getElementById('addCameraModal');
    if (modal) {
        modal.classList.add('hidden');
    }
}

function addCamera() {
    const name = document.getElementById('cameraName').value.trim();
    const source = document.getElementById('cameraSource').value.trim();
    const id = document.getElementById('cameraId').value.trim();
    
    if (!name) {
        alert('Please enter a camera name');
        return;
    }
    
    if (!source) {
        alert('Please enter a camera source');
        return;
    }
    
    const cameraData = {
        name: name,
        source: source
    };
    
    if (id) {
        cameraData.id = id;
    }
    
    fetch('/cameras/add', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(cameraData)
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            hideAddCameraModal();
            loadCameras();
            showNotification(`Camera "${name}" added successfully`, 'success');
        } else {
            alert('Failed to add camera: ' + (data.error || 'Unknown error'));
        }
    })
    .catch(err => {
        console.error('Add camera failed:', err);
        alert('Failed to add camera. Please try again.');
    });
}

function removeCamera(cameraId) {
    if (!confirm(`Are you sure you want to remove camera ${cameraId}?`)) {
        return;
    }
    
    fetch(`/cameras/${cameraId}/remove`, {
        method: 'POST'
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            loadCameras();
            showNotification(`Camera ${cameraId} removed`, 'info');
        } else {
            alert('Failed to remove camera: ' + (data.error || 'Unknown error'));
        }
    })
    .catch(err => {
        console.error('Remove camera failed:', err);
        alert('Failed to remove camera. Please try again.');
    });
}

function toggleFullscreen(cameraId) {
    const card = document.getElementById(`camera-${cameraId}`);
    if (!card) return;
    
    if (card.classList.contains('fullscreen')) {
        card.classList.remove('fullscreen');
        document.body.style.overflow = '';
    } else {
        // Remove fullscreen from others
        document.querySelectorAll('.camera-card.fullscreen').forEach(c => {
            c.classList.remove('fullscreen');
        });
        card.classList.add('fullscreen');
        document.body.style.overflow = 'hidden';
    }
}

function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.innerHTML = `
        <span>${message}</span>
        <button onclick="this.parentElement.remove()">×</button>
    `;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 20px;
        background: ${type === 'success' ? '#238636' : type === 'error' ? '#da3633' : '#58a6ff'};
        color: white;
        border-radius: 8px;
        display: flex;
        align-items: center;
        gap: 15px;
        z-index: 2000;
        animation: slideIn 0.3s ease;
    `;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.remove();
    }, 3000);
}

// Update camera threat status periodically
function updateCameraStatus() {
    fetch('/cameras')
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                data.cameras.forEach(camera => {
                    const card = document.getElementById(`camera-${camera.id}`);
                    if (card) {
                        if (camera.threat) {
                            card.classList.add('threat-active');
                        } else {
                            card.classList.remove('threat-active');
                        }
                    }
                });
            }
        })
        .catch(err => console.error('Camera status update failed:', err));
}

// Close modal on click outside
document.addEventListener('click', function(e) {
    const modal = document.getElementById('addCameraModal');
    if (modal && e.target === modal) {
        hideAddCameraModal();
    }
    const previewModal = document.getElementById('imagePreviewModal');
    if (previewModal && e.target === previewModal) {
        closeImagePreview();
    }
});

// Close modal on Escape key
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        hideAddCameraModal();
        closeImagePreview();
        // Exit fullscreen
        document.querySelectorAll('.camera-card.fullscreen').forEach(card => {
            card.classList.remove('fullscreen');
        });
        document.body.style.overflow = '';
    }
});

// ============ ALERTS GALLERY ============

let allGalleryAlerts = [];

function loadGallery() {
    fetch('/alerts?limit=100')
        .then(res => res.json())
        .then(data => {
            if (data.success && data.alerts) {
                allGalleryAlerts = data.alerts;
                renderGallery(allGalleryAlerts);
                updateGalleryStats(allGalleryAlerts);
            }
        })
        .catch(err => console.error('Failed to load gallery:', err));
}

function calculateSeverity(detections, notes) {
    // Parse detections from notes if available
    let personCount = 0;
    let vehicleCount = 0;
    
    if (notes) {
        const personMatch = notes.match(/(\d+)\s*person/i);
        const carMatch = notes.match(/(\d+)\s*car/i);
        const truckMatch = notes.match(/(\d+)\s*truck/i);
        const motorcycleMatch = notes.match(/(\d+)\s*motorcycle/i);
        const busMatch = notes.match(/(\d+)\s*bus/i);
        
        if (personMatch) personCount = parseInt(personMatch[1]);
        if (carMatch) vehicleCount += parseInt(carMatch[1]);
        if (truckMatch) vehicleCount += parseInt(truckMatch[1]);
        if (motorcycleMatch) vehicleCount += parseInt(motorcycleMatch[1]);
        if (busMatch) vehicleCount += parseInt(busMatch[1]);
    }
    
    // If no counts in notes, estimate from detection_type
    if (personCount === 0 && vehicleCount === 0) {
        const type = (detections || '').toLowerCase();
        if (type.includes('person')) personCount = 1;
        if (type.includes('car') || type.includes('truck') || type.includes('motorcycle') || type.includes('bus')) vehicleCount = 1;
    }
    
    const totalThreats = personCount + vehicleCount;
    
    if (totalThreats >= 5 || personCount >= 3) {
        return { level: 'critical', label: '🔴 Critical', color: '#da3633' };
    } else if (totalThreats >= 3 || personCount >= 2) {
        return { level: 'high', label: '🟠 High', color: '#f0883e' };
    } else if (totalThreats >= 2 || personCount >= 1) {
        return { level: 'medium', label: '🟡 Medium', color: '#d29922' };
    } else {
        return { level: 'low', label: '🟢 Low', color: '#238636' };
    }
}

function renderGallery(alerts) {
    const grid = document.getElementById('galleryGrid');
    if (!grid) return;
    
    if (!alerts || alerts.length === 0) {
        grid.innerHTML = '<p class="no-alerts">No alert images yet</p>';
        return;
    }
    
    let html = '';
    alerts.forEach(alert => {
        const imagePath = (alert.image_path || '').replace(/\\/g, '/');
        const severity = calculateSeverity(alert.detection_type, alert.notes);
        const time = new Date(alert.timestamp);
        const timeStr = time.toLocaleString('en-US', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            hour12: true
        });
        
        const detectionType = alert.detection_type || 'Unknown';
        const confidence = alert.confidence ? Math.round(alert.confidence * 100) : 'N/A';
        
        // Extract camera ID from notes
        const notes = alert.notes || '';
        const cameraMatch = notes.match(/\[CAM_\d+\]/);
        const cameraId = cameraMatch ? cameraMatch[0].replace(/[\[\]]/g, '') : 'CAM_001';
        
        html += `
            <div class="gallery-card" data-severity="${severity.level}" data-type="${detectionType.toLowerCase()}" onclick="openImagePreview(${alert.id}, '${imagePath}', '${detectionType}', '${severity.level}', '${severity.label}', ${alert.confidence || 0}, '${alert.timestamp}', '${(alert.notes || '').replace(/'/g, "\\'")}')">
                <div class="gallery-image">
                    <img src="/${imagePath}" alt="Alert" onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 200 150%22><rect fill=%22%23161b22%22 width=%22200%22 height=%22150%22/><text x=%22100%22 y=%2280%22 fill=%22%238b949e%22 text-anchor=%22middle%22 font-size=%2214%22>No Image</text></svg>'">
                    <div class="gallery-severity-badge" style="background: ${severity.color}">
                        ${severity.label}
                    </div>
                    <div class="gallery-camera-badge">
                        📹 ${cameraId}
                    </div>
                </div>
                <div class="gallery-info">
                    <div class="gallery-type">
                        ${getTypeIcon(detectionType)} ${formatDetectionType(detectionType)}
                    </div>
                    <div class="gallery-meta">
                        <span class="gallery-time">🕐 ${timeStr}</span>
                        <span class="gallery-confidence">${confidence}%</span>
                    </div>
                </div>
            </div>
        `;
    });
    
    grid.innerHTML = html;
}

function getTypeIcon(type) {
    const t = type.toLowerCase();
    if (t.includes('person')) return '👤';
    if (t.includes('car')) return '🚗';
    if (t.includes('truck')) return '🚛';
    if (t.includes('motorcycle')) return '🏍️';
    if (t.includes('bus')) return '🚌';
    return '⚠️';
}

function formatDetectionType(type) {
    return type.split(',').map(t => {
        const trimmed = t.trim().toLowerCase();
        if (trimmed === 'person') return 'Human';
        return trimmed.charAt(0).toUpperCase() + trimmed.slice(1);
    }).join(', ');
}

function updateGalleryStats(alerts) {
    let total = alerts.length;
    let critical = 0, high = 0, medium = 0, low = 0;
    
    alerts.forEach(alert => {
        const severity = calculateSeverity(alert.detection_type, alert.notes);
        switch(severity.level) {
            case 'critical': critical++; break;
            case 'high': high++; break;
            case 'medium': medium++; break;
            case 'low': low++; break;
        }
    });
    
    document.getElementById('galleryTotal').textContent = total;
    document.getElementById('galleryCritical').textContent = critical;
    document.getElementById('galleryHigh').textContent = high;
    document.getElementById('galleryMedium').textContent = medium;
    document.getElementById('galleryLow').textContent = low;
}

function filterGallery() {
    const severityFilter = document.getElementById('severityFilter').value;
    const typeFilter = document.getElementById('typeFilter').value;
    
    let filtered = allGalleryAlerts;
    
    if (severityFilter !== 'all') {
        filtered = filtered.filter(alert => {
            const severity = calculateSeverity(alert.detection_type, alert.notes);
            return severity.level === severityFilter;
        });
    }
    
    if (typeFilter !== 'all') {
        filtered = filtered.filter(alert => {
            return (alert.detection_type || '').toLowerCase().includes(typeFilter);
        });
    }
    
    renderGallery(filtered);
}

function openImagePreview(id, imagePath, type, severityLevel, severityLabel, confidence, timestamp, notes) {
    const modal = document.getElementById('imagePreviewModal');
    const previewImage = document.getElementById('previewImage');
    const previewType = document.getElementById('previewType');
    const previewSeverity = document.getElementById('previewSeverity');
    const previewConfidence = document.getElementById('previewConfidence');
    const previewTime = document.getElementById('previewTime');
    const previewCamera = document.getElementById('previewCamera');
    
    previewImage.src = '/' + imagePath;
    previewType.innerHTML = `${getTypeIcon(type)} ${formatDetectionType(type)}`;
    previewSeverity.innerHTML = severityLabel;
    previewSeverity.className = `severity-${severityLevel}`;
    previewConfidence.textContent = confidence ? `${Math.round(confidence * 100)}%` : 'N/A';
    previewTime.textContent = new Date(timestamp).toLocaleString('en-US', {
        weekday: 'short',
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: true
    });
    
    // Extract camera from notes
    const cameraMatch = notes.match(/\[CAM_\d+\]/);
    previewCamera.textContent = cameraMatch ? cameraMatch[0].replace(/[\[\]]/g, '') : 'CAM_001';
    
    modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
}

function closeImagePreview() {
    const modal = document.getElementById('imagePreviewModal');
    if (modal) {
        modal.classList.add('hidden');
        document.body.style.overflow = '';
    }
}

// ============ LIVE TAB IMAGE DETECTION ============

let liveSelectedFile = null;

function initLiveImageDetection() {
    const liveImageInput = document.getElementById('liveImageInput');
    const liveUploadArea = document.getElementById('liveUploadArea');
    const liveImagePreview = document.getElementById('liveImagePreview');
    const livePreviewImg = document.getElementById('livePreviewImg');
    const liveScanResults = document.getElementById('liveScanResults');
    
    if (!liveImageInput || !liveUploadArea) return;
    
    liveImageInput.addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (file) {
            liveSelectedFile = file;
            const reader = new FileReader();
            reader.onload = function(e) {
                livePreviewImg.src = e.target.result;
                liveUploadArea.style.display = 'none';
                liveImagePreview.classList.remove('hidden');
                liveScanResults.classList.add('hidden');
            };
            reader.readAsDataURL(file);
        }
    });
    
    // Drag and drop for live tab
    liveUploadArea.addEventListener('dragover', function(e) {
        e.preventDefault();
        liveUploadArea.classList.add('drag-over');
    });
    
    liveUploadArea.addEventListener('dragleave', function(e) {
        e.preventDefault();
        liveUploadArea.classList.remove('drag-over');
    });
    
    liveUploadArea.addEventListener('drop', function(e) {
        e.preventDefault();
        liveUploadArea.classList.remove('drag-over');
        
        const file = e.dataTransfer.files[0];
        if (file && file.type.startsWith('image/')) {
            liveSelectedFile = file;
            const reader = new FileReader();
            reader.onload = function(e) {
                livePreviewImg.src = e.target.result;
                liveUploadArea.style.display = 'none';
                liveImagePreview.classList.remove('hidden');
                liveScanResults.classList.add('hidden');
            };
            reader.readAsDataURL(file);
        }
    });
}

async function analyzeLiveImage() {
    if (!liveSelectedFile) return;
    
    const liveScanResults = document.getElementById('liveScanResults');
    const liveScanContent = document.getElementById('liveScanContent');
    const liveUploadArea = document.getElementById('liveUploadArea');
    const liveImagePreview = document.getElementById('liveImagePreview');
    
    // Show loading state
    liveScanResults.classList.remove('hidden');
    liveScanContent.innerHTML = '<div class="scan-result-item"><span class="icon">⏳</span><span class="label">Analyzing image...</span></div>';
    
    const formData = new FormData();
    formData.append('image', liveSelectedFile);
    
    try {
        const res = await fetch('/upload', { method: 'POST', body: formData });
        const data = await res.json();
        
        if (data.success) {
            if (data.threat_detected) {
                // Parse detections from message
                const detections = data.detections || [];
                let resultsHtml = '';
                
                if (detections.length > 0) {
                    detections.forEach(det => {
                        const icon = det.type === 'person' ? '👤' : '🐾';
                        const label = det.type === 'person' ? 'Human' : det.type.charAt(0).toUpperCase() + det.type.slice(1);
                        const confidence = Math.round(det.confidence * 100);
                        resultsHtml += `
                            <div class="scan-result-item">
                                <span class="icon">${icon}</span>
                                <span class="label">${label}</span>
                                <span class="confidence">${confidence}%</span>
                            </div>
                        `;
                    });
                } else {
                    resultsHtml = `
                        <div class="scan-result-item">
                            <span class="icon">⚠️</span>
                            <span class="label">Threat Detected</span>
                        </div>
                    `;
                }
                
                liveScanContent.innerHTML = resultsHtml;
                liveScanContent.className = 'scan-result-content threat';
                
                // Refresh alerts
                updateAlerts();
                loadGallery();
            } else {
                liveScanContent.innerHTML = `
                    <div class="scan-result-item">
                        <span class="icon">✅</span>
                        <span class="label">No threats detected</span>
                    </div>
                `;
                liveScanContent.className = 'scan-result-content safe';
            }
        } else {
            liveScanContent.innerHTML = `
                <div class="scan-result-item">
                    <span class="icon">❌</span>
                    <span class="label">Error: ${data.error}</span>
                </div>
            `;
            liveScanContent.className = 'scan-result-content';
        }
    } catch (err) {
        liveScanContent.innerHTML = `
            <div class="scan-result-item">
                <span class="icon">❌</span>
                <span class="label">Analysis failed</span>
            </div>
        `;
        liveScanContent.className = 'scan-result-content';
    }
    
    // Reset for new upload after delay
    setTimeout(() => {
        liveUploadArea.style.display = 'flex';
        liveImagePreview.classList.add('hidden');
        liveSelectedFile = null;
    }, 4000);
}

// Initialize live image detection when DOM is ready
setTimeout(initLiveImageDetection, 100);

// Initialize
updateAlerts();
checkSystemStatus();
loadCameras();
setInterval(updateAlerts, 2000);
setInterval(checkSystemStatus, 1000);
setInterval(updateCameraStatus, 2000);
