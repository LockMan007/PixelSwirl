document.addEventListener('DOMContentLoaded', () => {
    // A simple color interpolation function
    const hexToRgb = (hex) => {
        const bigint = parseInt(hex.slice(1), 16);
        const r = (bigint >> 16) & 255;
        const g = (bigint >> 8) & 255;
        const b = bigint & 255;
        return [r, g, b];
    };

    const rgbToHex = (r, g, b) => '#' + ((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1);

    const interpolateColor = (color1, color2, ratio) => {
        const [r1, g1, b1] = hexToRgb(color1);
        const [r2, g2, b2] = hexToRgb(color2);

        const r = Math.round(r1 + (r2 - r1) * ratio);
        const g = Math.round(g1 + (g2 - g1) * ratio);
        const b = Math.round(b1 + (b2 - b1) * ratio);

        return rgbToHex(r, g, b);
    };

    const getBgColor = (progress) => {
        const green = "#00FF00";
        const yellow = "#FFFF00";
        const red = "#FF0000";

        if (progress < 0.5) {
            const ratio = progress / 0.5;
            return interpolateColor(green, yellow, ratio);
        } else {
            const ratio = (progress - 0.5) / 0.5;
            return interpolateColor(yellow, red, ratio);
        }
    };

    // Formats a timedelta into a concise string
    const formatCountdownTimer = (totalSeconds) => {
        if (totalSeconds <= 0) return "Time's Up!";

        const years = Math.floor(totalSeconds / (365 * 24 * 3600));
        totalSeconds %= (365 * 24 * 3600);
        const months = Math.floor(totalSeconds / (30 * 24 * 3600));
        totalSeconds %= (30 * 24 * 3600);
        const days = Math.floor(totalSeconds / (24 * 3600));
        totalSeconds %= (24 * 3600);
        const hours = Math.floor(totalSeconds / 3600);
        totalSeconds %= 3600;
        const minutes = Math.floor(totalSeconds / 60);
        const seconds = Math.floor(totalSeconds % 60);

        const parts = [];
        if (years > 0) parts.push(`${years}y`);
        if (months > 0) parts.push(`${months}m`);
        if (days > 0) parts.push(`${days}d`);

        if (parts.length === 0) {
            return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
        }
        
        if (hours > 0) parts.push(`${hours}h`);
        if (minutes > 0 && parts.length < 3) parts.push(`${minutes}m`);

        return parts.join(' ');
    };

    const calculatePosition = (lastCompletedDate, frequencyDays, canvasHeight) => {
        const timeElapsed = (new Date() - lastCompletedDate) / 1000; // in seconds
        const totalTime = frequencyDays * 24 * 60 * 60; // in seconds
        const progress = Math.min(timeElapsed / totalTime, 1.0);

        const padding = 30;
        const minY = padding;
        const maxY = canvasHeight - padding;

        return minY + progress * (maxY - minY);
    };

    const renderGoals = (goals) => {
        const container = document.querySelector('.goal-container');
        container.innerHTML = ''; // Clear existing content

        goals.forEach(goal => {
            const lastCompletedDate = new Date(goal.last_completed_date);
            
            const frequencyDays = goal.frequency_days + goal.frequency_hours / 24 + goal.frequency_minutes / (24 * 60);
            
            const column = document.createElement('div');
            column.className = 'goal-column';
            column.dataset.id = goal.id;
            column.dataset.lastCompleted = lastCompletedDate.toISOString();
            column.dataset.frequency = frequencyDays;
            
            const timerLabel = document.createElement('div');
            timerLabel.className = 'timer';
            column.appendChild(timerLabel);
            
            const canvasWrapper = document.createElement('div');
            canvasWrapper.className = 'canvas-wrapper';
            
            const balloonImage = document.createElement('img');
            balloonImage.className = 'balloon-image';
            balloonImage.src = goal.image_path ? `images/${goal.image_path}` : 'images/default_balloon.png';
            balloonImage.style.top = `${calculatePosition(lastCompletedDate, frequencyDays, 400)}px`;
            
            canvasWrapper.appendChild(balloonImage);
            column.appendChild(canvasWrapper);
            
            const goalName = document.createElement('div');
            goalName.className = 'goal-name';
            goalName.textContent = goal.name;
            column.appendChild(goalName);
            
            container.appendChild(column);
        });
        updateUI(); // Initial UI update after rendering
    };

    const updateUI = () => {
        document.querySelectorAll('.goal-column').forEach(column => {
            const lastCompleted = new Date(column.dataset.lastCompleted);
            const frequency = parseFloat(column.dataset.frequency);

            const timeElapsed = (new Date() - lastCompleted) / 1000;
            const totalTime = frequency * 24 * 60 * 60;
            const progress = Math.min(timeElapsed / totalTime, 1.0);

            const balloonImage = column.querySelector('.balloon-image');
            balloonImage.style.top = `${calculatePosition(lastCompleted, frequency, 400)}px`;

            const canvasWrapper = column.querySelector('.canvas-wrapper');
            canvasWrapper.style.backgroundColor = getBgColor(progress);

            const timeRemaining = totalTime - timeElapsed;
            const timerLabel = column.querySelector('.timer');
            timerLabel.textContent = formatCountdownTimer(timeRemaining);
        });
    };

    const loadButton = document.getElementById('load-goals-btn');
    const fileInput = document.getElementById('goals-file-input');

    loadButton.addEventListener('click', () => {
        fileInput.click();
    });

    fileInput.addEventListener('change', (event) => {
        const file = event.target.files[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = (e) => {
            try {
                const data = JSON.parse(e.target.result);
                renderGoals(data.goals);
            } catch (error) {
                alert("Error parsing JSON file. Please ensure it's a valid goals.json.");
                console.error("JSON parsing error:", error);
            }
        };
        reader.readAsText(file);
    });

    setInterval(updateUI, 1000);
});