/* TwinSync Spot - Client JavaScript */

// Resolve ingress/base path even when the server couldn't inject it
function detectBasePath() {
    if (typeof INGRESS_PATH !== 'undefined' && INGRESS_PATH) {
        return INGRESS_PATH;
    }

    const match = window.location.pathname.match(/^\/api\/hassio_ingress\/[^/]+/);
    if (match) {
        return match[0];
    }

    return '';
}

const BASE_PATH = detectBasePath();

/**
 * Make API request
 */
async function api(endpoint, options = {}) {
    const url = BASE_PATH + endpoint;
    
    const defaultHeaders = {
        'Content-Type': 'application/json',
    };
    
    const response = await fetch(url, {
        ...options,
        headers: {
            ...defaultHeaders,
            ...options.headers,
        },
    });
    
    if (!response.ok) {
        const text = await response.text();
        throw new Error(text || `HTTP ${response.status}`);
    }
    
    return response.json();
}

/**
 * Show toast notification
 */
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.remove();
    }, 4000);
}

/**
 * Check a spot
 */
async function checkSpot(spotId) {
    showToast('Checking spot...', 'info');
    
    try {
        const result = await api(`/api/spots/${spotId}/check`, {
            method: 'POST',
        });
        
        if (result.error_message) {
            showToast('Error: ' + result.error_message, 'error');
        } else if (result.status === 'sorted') {
            showToast('Looking good! ✅', 'success');
        } else {
            showToast(`Found ${result.to_sort?.length || 0} items to sort`, 'info');
        }
        
        // Reload page to show new state
        if (typeof loadSpots === 'function') {
            loadSpots();
        } else if (typeof loadSpot === 'function') {
            loadSpot();
        } else {
            location.reload();
        }
        
    } catch (err) {
        showToast('Check failed: ' + err.message, 'error');
    }
}

/**
 * Reset a spot (mark as fixed)
 */
async function resetSpot(spotId) {
    try {
        const result = await api(`/api/spots/${spotId}/reset`, {
            method: 'POST',
        });
        
        showToast('Spot reset! Streak: ' + result.new_streak, 'success');
        
        if (typeof loadSpots === 'function') {
            loadSpots();
        } else if (typeof loadSpot === 'function') {
            loadSpot();
        } else {
            location.reload();
        }
        
    } catch (err) {
        showToast('Reset failed: ' + err.message, 'error');
    }
}

/**
 * Snooze a spot
 */
async function snoozeSpot(spotId, minutes = 30) {
    try {
        await api(`/api/spots/${spotId}/snooze`, {
            method: 'POST',
            body: JSON.stringify({ minutes }),
        });
        
        showToast(`Snoozed for ${minutes} minutes 😴`, 'success');
        
        if (typeof loadSpots === 'function') {
            loadSpots();
        } else if (typeof loadSpot === 'function') {
            loadSpot();
        } else {
            location.reload();
        }
        
    } catch (err) {
        showToast('Snooze failed: ' + err.message, 'error');
    }
}

/**
 * Unsnooze a spot
 */
async function unsnoozeSpot(spotId) {
    try {
        await api(`/api/spots/${spotId}/unsnooze`, {
            method: 'POST',
        });
        
        showToast('Spot woken up! ⏰', 'success');
        
        if (typeof loadSpots === 'function') {
            loadSpots();
        } else if (typeof loadSpot === 'function') {
            loadSpot();
        } else {
            location.reload();
        }
        
    } catch (err) {
        showToast('Unsnooze failed: ' + err.message, 'error');
    }
}

/**
 * Delete a spot
 */
async function deleteSpot(spotId) {
    if (!confirm('Are you sure you want to delete this spot? This cannot be undone.')) {
        return;
    }
    
    try {
        await api(`/api/spots/${spotId}`, {
            method: 'DELETE',
        });
        
        showToast('Spot deleted', 'success');
        window.location.href = BASE_PATH + '/';
        
    } catch (err) {
        showToast('Delete failed: ' + err.message, 'error');
    }
}

/**
 * Check all spots
 */
async function checkAllSpots() {
    showToast('Checking all spots...', 'info');
    
    try {
        const result = await api('/api/check-all', {
            method: 'POST',
        });
        
        const sorted = result.results.filter(r => r.status === 'sorted').length;
        const needsAttention = result.results.filter(r => r.status === 'needs_attention').length;
        
        showToast(`Done! ${sorted} sorted, ${needsAttention} need attention`, 'success');
        
        if (typeof loadSpots === 'function') {
            loadSpots();
        } else {
            location.reload();
        }
        
    } catch (err) {
        showToast('Check all failed: ' + err.message, 'error');
    }
}
