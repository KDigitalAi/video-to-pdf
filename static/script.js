let currentJobId = null;
let statusCheckInterval = null;

document.getElementById('fileInput').addEventListener('change', function(e) {
    const file = e.target.files[0];
    const fileNameDiv = document.getElementById('fileName');
    
    if (file) {
        fileNameDiv.textContent = `Selected: ${file.name}`;
        fileNameDiv.style.display = 'block';
    } else {
        fileNameDiv.textContent = '';
        fileNameDiv.style.display = 'none';
    }
});

document.getElementById('uploadForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const fileInput = document.getElementById('fileInput');
    const file = fileInput.files[0];
    
    if (!file) {
        alert('Please select a CSV file');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', file);
    
    const uploadBtn = document.getElementById('uploadBtn');
    const btnText = uploadBtn.querySelector('.btn-text');
    const btnLoader = uploadBtn.querySelector('.btn-loader');
    
    // Show loading state
    uploadBtn.disabled = true;
    btnText.style.display = 'none';
    btnLoader.style.display = 'inline';
    
    try {
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            currentJobId = data.job_id;
            
            // Hide upload section, show processing section
            document.getElementById('uploadSection').style.display = 'none';
            document.getElementById('processingSection').style.display = 'block';
            document.getElementById('resultSection').style.display = 'none';
            
            // Start polling for status
            startStatusPolling(currentJobId);
        } else {
            alert('Upload failed: ' + (data.error || 'Unknown error'));
            resetButton();
        }
    } catch (error) {
        console.error('Upload error:', error);
        alert('Upload failed: ' + error.message);
        resetButton();
    }
});

function resetButton() {
    const uploadBtn = document.getElementById('uploadBtn');
    const btnText = uploadBtn.querySelector('.btn-text');
    const btnLoader = uploadBtn.querySelector('.btn-loader');
    
    uploadBtn.disabled = false;
    btnText.style.display = 'inline';
    btnLoader.style.display = 'none';
}

function startStatusPolling(jobId) {
    // Clear any existing interval
    if (statusCheckInterval) {
        clearInterval(statusCheckInterval);
    }
    
    // Check status immediately
    checkStatus(jobId);
    
    // Then check every 2 seconds
    statusCheckInterval = setInterval(() => {
        checkStatus(jobId);
    }, 2000);
}

async function checkStatus(jobId) {
    try {
        const response = await fetch(`/status/${jobId}`);
        const data = await response.json();
        
        if (!data.success) {
            console.error('Status check failed:', data.error);
            return;
        }
        
        const status = data.status;
        const progress = data.progress || 0;
        const message = data.message || '';
        
        // Update progress bar
        document.getElementById('progressFill').style.width = progress + '%';
        document.getElementById('progressText').textContent = progress + '%';
        document.getElementById('statusMessage').textContent = message;
        
        if (status === 'completed') {
            // Stop polling
            clearInterval(statusCheckInterval);
            
            // Show result section
            document.getElementById('processingSection').style.display = 'none';
            document.getElementById('resultSection').style.display = 'block';
            document.getElementById('successBox').style.display = 'block';
            document.getElementById('errorBox').style.display = 'none';
            document.getElementById('resultMessage').textContent = message || 'Your PDF is ready for download!';
            
            // Set up download button
            document.getElementById('downloadBtn').onclick = () => {
                window.location.href = `/download/${jobId}`;
            };
            
            // Scroll to result section
            document.getElementById('resultSection').scrollIntoView({ behavior: 'smooth', block: 'start' });
            
        } else if (status === 'error') {
            // Stop polling
            clearInterval(statusCheckInterval);
            
            // Show error section
            document.getElementById('processingSection').style.display = 'none';
            document.getElementById('resultSection').style.display = 'block';
            document.getElementById('successBox').style.display = 'none';
            document.getElementById('errorBox').style.display = 'block';
            document.getElementById('errorMessage').textContent = data.error || 'Unknown error occurred';
            
            // Scroll to result section
            document.getElementById('resultSection').scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
        // If status is 'processing', continue polling
        
    } catch (error) {
        console.error('Status check error:', error);
    }
}

function resetForm() {
    // Clear file input
    document.getElementById('fileInput').value = '';
    document.getElementById('fileName').textContent = '';
    document.getElementById('fileName').style.display = 'none';
    
    // Reset sections
    document.getElementById('uploadSection').style.display = 'block';
    document.getElementById('processingSection').style.display = 'none';
    document.getElementById('resultSection').style.display = 'none';
    
    // Reset button
    resetButton();
    
    // Clear intervals
    if (statusCheckInterval) {
        clearInterval(statusCheckInterval);
        statusCheckInterval = null;
    }
    
    currentJobId = null;
}

