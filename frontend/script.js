const uploadBtn = document.getElementById('upload');
const searchBtn = document.getElementById('search');
const message = document.getElementById('message');
const resultsDiv = document.getElementById('results');

let currentWorkspaceId; // To keep track of the active workspace for searching

// A generic function to handle API requests and errors
async function handleRequest(url, options, errorMessage) {
    try {
        const response = await fetch(url, options);
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || `HTTP error! status: ${response.status}`);
        }
        return data;
    } catch (error) {
        message.textContent = `${errorMessage}: ${error.message}`;
        console.error(errorMessage, error);
        return null;
    }
}

// Function to find a user by name, or create them if they don't exist
async function getOrCreateUser(username) {
    message.textContent = `Checking for user '${username}'...`;
    let users = await handleRequest(
        `http://localhost:8000/users/?username=${encodeURIComponent(username)}`,
        { method: 'GET' },
        'Failed to get user'
    );

    if (users && users.length > 0) {
        message.textContent = `User '${username}' found.`;
        return users[0];
    }

    message.textContent = `User '${username}' not found. Creating...`;
    return await handleRequest(
        'http://localhost:8000/users/',
        {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username }),
        },
        'Failed to create user'
    );
}

// Function to find a workspace, or create it if it doesn't exist
async function getOrCreateWorkspace(workspaceName, userId) {
    message.textContent = `Checking for workspace '${workspaceName}'...`;
    let workspaces = await handleRequest(
        `http://localhost:8000/workspaces/?name=${encodeURIComponent(workspaceName)}&owner_id=${userId}`,
        { method: 'GET' },
        'Failed to get workspace'
    );

    if (workspaces && workspaces.length > 0) {
        message.textContent = `Workspace '${workspaceName}' found.`;
        return workspaces[0];
    }

    message.textContent = `Workspace '${workspaceName}' not found. Creating...`;
    return await handleRequest(
        'http://localhost:8000/workspaces/',
        {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: workspaceName, owner_id: userId }),
        },
        'Failed to create workspace'
    );
}

// Search function
async function performSearch() {
    const query = document.getElementById('searchQuery').value;
    if (!query) {
        resultsDiv.innerHTML = 'Please enter a search query.';
        return;
    }
    if (!currentWorkspaceId) {
        resultsDiv.innerHTML = 'Please upload a file first to establish a workspace context.';
        return;
    }

    resultsDiv.innerHTML = 'Searching...';

    const searchResults = await handleRequest(
        `http://localhost:8001/search/?query=${encodeURIComponent(query)}&workspace_id=${currentWorkspaceId}`,
        { method: 'GET' },
        'Search failed'
    );

    if (searchResults && searchResults.length > 0) {
        resultsDiv.innerHTML = ''; // Clear previous results
        for (const hit of searchResults) {
            const resultElement = document.createElement('div');
            resultElement.innerHTML = `
                <div>
                    <strong>File:</strong> ${hit.payload.s3_key} | 
                    <strong>Score:</strong> ${hit.score.toFixed(4)}
                    <button class="toggle-content" data-s3-key="${hit.payload.s3_key}">Show Content</button>
                </div>
                <div class="content" style="display: none; white-space: pre-wrap; background: #f4f4f4; padding: 10px; margin-top: 5px;"></div>
                <hr/>
            `;
            resultsDiv.appendChild(resultElement);
        }

        // Add event listeners to all new "Show/Hide" buttons
        document.querySelectorAll('.toggle-content').forEach(button => {
            button.addEventListener('click', toggleContent);
        });
    } else if (searchResults) {
        resultsDiv.innerHTML = 'No results found.';
    }
}

async function toggleContent(event) {
    const button = event.target;
    const s3_key = button.dataset.s3Key;
    const contentDiv = button.parentElement.nextElementSibling;

    // If content is already visible, hide it and return
    if (contentDiv.style.display === 'block') {
        contentDiv.style.display = 'none';
        button.textContent = 'Show Content';
        return;
    }

    // If content has already been loaded, just show it
    if (contentDiv.innerHTML.trim() !== '') {
        contentDiv.style.display = 'block';
        button.textContent = 'Hide Content';
        return;
    }
    
    // Otherwise, fetch the content
    button.textContent = 'Loading...';
    const data = await handleRequest(
        `http://localhost:8000/file-content/?s3_key=${encodeURIComponent(s3_key)}`,
        { method: 'GET' },
        'Failed to fetch file content'
    );

    if (data) {
        contentDiv.textContent = data.content;
        contentDiv.style.display = 'block';
        button.textContent = 'Hide Content';
    } else {
        button.textContent = 'Show Content'; // Reset button on failure
    }
}

// Main upload logic
uploadBtn.addEventListener('click', async () => {
    // 1. Get all necessary inputs
    const username = document.getElementById('username').value;
    const workspaceName = document.getElementById('workspace').value;
    const fileInput = document.getElementById('file');
    const files = fileInput.files;

    if (!username || !workspaceName || files.length === 0) {
        message.textContent = 'Please fill in all fields and choose at least one file.';
        return;
    }

    // 2. Get or create the user
    const user = await getOrCreateUser(username);
    if (!user) return; // Stop if user creation failed

    // 3. Get or create the workspace
    const workspace = await getOrCreateWorkspace(workspaceName, user.id);
    if (!workspace) return; // Stop if workspace creation failed
    currentWorkspaceId = workspace.id; // Set the current workspace for searching

    // 4. Upload the files sequentially
    for (let i = 0; i < files.length; i++) {
        const file = files[i];
        message.textContent = `Uploading file ${i + 1} of ${files.length}: '${file.name}'...`;
        
        const formData = new FormData();
        formData.append('file', file);

        const uploadResult = await handleRequest(
            `http://localhost:8000/uploadfile/?workspace_id=${workspace.id}`,
            {
                method: 'POST',
                body: formData,
            },
            `Failed to upload file '${file.name}'`
        );
        
        if (!uploadResult) {
            message.textContent += ' Halting upload process.';
            return; // Stop the batch if any file fails
        }
    }
    
    message.textContent = `Successfully uploaded all ${files.length} files!`;
});

searchBtn.addEventListener('click', performSearch); 