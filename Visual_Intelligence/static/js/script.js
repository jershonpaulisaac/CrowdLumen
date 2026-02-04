function updateStatus() {
    fetch('/status')
        .then(response => response.json())
        .then(data => {
            // Update Threat Level
            const threatEl = document.getElementById('threat-indicator');
            threatEl.textContent = data.threat_level;
            threatEl.style.color = data.threat_color;
            
            // Update Reason
            const reasonEl = document.getElementById('reason-text');
            reasonEl.textContent = data.reason;
            
            // Update Count
            document.getElementById('person-count').textContent = data.person_count;
            
            // Update Chaos Bar
            const chaosBar = document.getElementById('chaos-bar');
            chaosBar.style.width = data.chaos_metric + '%';
            
            // Color code the chaos bar based on intensity
            if (data.chaos_metric > 70) chaosBar.style.backgroundColor = 'var(--status-critical)';
            else if (data.chaos_metric > 40) chaosBar.style.backgroundColor = 'var(--status-warning)';
            else chaosBar.style.backgroundColor = 'var(--accent)';
        })
        .catch(err => console.error("Error fetching status:", err));
}

function switchCamera(index) {
    // Update UI Buttons
    const buttons = document.querySelectorAll('.cam-btn');
    buttons.forEach((btn, idx) => {
        if (idx === index) btn.classList.add('active');
        else btn.classList.remove('active');
    });

    // Send Request
    fetch('/switch_camera', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ index: index }),
    })
    .then(response => response.json())
    .then(data => {
        console.log("Camera switched to:", data.current_index);
    });
}

// Poll every 500ms
setInterval(updateStatus, 500);
