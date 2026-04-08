let currentJobId = null;
let statusCheckInterval = null;

document.getElementById('fileInput').addEventListener('change', function(e) {
    const files = e.target.files;
    const fileNameDiv = document.getElementById('fileName');

    if (files && files.length > 0) {
        const names = Array.from(files).map((f) => f.name);
        const summary =
            files.length === 1
                ? `Selected: ${names[0]}`
                : `Selected ${files.length} files:\n${names.join('\n')}`;
        fileNameDiv.textContent = summary;
        fileNameDiv.style.display = 'block';
        fileNameDiv.style.whiteSpace = 'pre-line';
    } else {
        fileNameDiv.textContent = '';
        fileNameDiv.style.display = 'none';
    }
});

document.getElementById('uploadForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const fileInput = document.getElementById('fileInput');
    const files = fileInput.files;

    if (!files || files.length === 0) {
        alert('Please select a CSV or one or more VTT files');
        return;
    }

    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
        formData.append('files', files[i]);
    }
    
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

            const errList = document.getElementById('fileErrorsList');
            const fileErrors = data.file_errors || [];
            if (fileErrors.length > 0) {
                errList.innerHTML = fileErrors.map((line) => `<li>${escapeHtml(line)}</li>`).join('');
                errList.style.display = 'block';
            } else {
                errList.innerHTML = '';
                errList.style.display = 'none';
            }
            
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
            const errListOk = document.getElementById('fileErrorsList');
            errListOk.innerHTML = '';
            errListOk.style.display = 'none';
            
            // Scroll to result section
            document.getElementById('resultSection').scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
        // If status is 'processing', continue polling
        
    } catch (error) {
        console.error('Status check error:', error);
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function resetForm() {
    // Clear file input
    document.getElementById('fileInput').value = '';
    document.getElementById('fileName').textContent = '';
    document.getElementById('fileName').style.display = 'none';
    const errList = document.getElementById('fileErrorsList');
    if (errList) {
        errList.innerHTML = '';
        errList.style.display = 'none';
    }
    
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

