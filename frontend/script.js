const uploadBtn = document.getElementById('upload');
const searchBtn = document.getElementById('search');
const selectWorkspaceBtn = document.getElementById('selectWorkspace');
const uploadMessage = document.getElementById('uploadMessage');
const workspaceMessage = document.getElementById('workspaceMessage');
const resultsDiv = document.getElementById('results');
const searchSection = document.getElementById('searchSection');

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
        console.error(errorMessage, error);
        // Show error message to user
        if (errorMessage.includes('upload')) {
            uploadMessage.textContent = `${errorMessage}: ${error.message}`;
            uploadMessage.className = 'error';
        } else if (errorMessage.includes('workspace') || errorMessage.includes('user')) {
            workspaceMessage.textContent = `${errorMessage}: ${error.message}`;
            workspaceMessage.className = 'error';
        }
        return null;
    }
}

// Function to find a user by name, or create them if they don't exist
async function getOrCreateUser(username) {
    uploadMessage.textContent = `Checking for user '${username}'...`;
    uploadMessage.className = '';
    
    // First, try to find the user
    const existingUser = await handleRequest(
        `http://localhost:8000/users/?username=${encodeURIComponent(username)}`,
        { method: 'GET' },
        'Failed to check for existing user'
    );

    if (existingUser && existingUser.length > 0) {
        uploadMessage.textContent = `Found existing user '${username}'`;
        return existingUser[0];
    }

    // If user doesn't exist, create them
    uploadMessage.textContent = `Creating new user '${username}'...`;
    const newUser = await handleRequest(
        'http://localhost:8000/users/',
        {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: username }),
        },
        'Failed to create user'
    );

    if (newUser) {
        uploadMessage.textContent = `Successfully created user '${username}'`;
        return newUser;
    }
    
    uploadMessage.textContent = 'Failed to create user';
    return null;
}

async function getOrCreateWorkspace(workspaceName, userId) {
    uploadMessage.textContent = `Checking for workspace '${workspaceName}'...`;
    
    // First, try to find the workspace for this user
    const existingWorkspace = await handleRequest(
        `http://localhost:8000/workspaces/?owner_id=${userId}&name=${encodeURIComponent(workspaceName)}`,
        { method: 'GET' },
        'Failed to check for existing workspace'
    );

    if (existingWorkspace && existingWorkspace.length > 0) {
        uploadMessage.textContent = `Found existing workspace '${workspaceName}'`;
        return existingWorkspace[0];
    }

    // If workspace doesn't exist, create it
    uploadMessage.textContent = `Creating new workspace '${workspaceName}'...`;
    const newWorkspace = await handleRequest(
        'http://localhost:8000/workspaces/',
        {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: workspaceName, owner_id: userId }),
        },
        'Failed to create workspace'
    );

    if (newWorkspace) {
        uploadMessage.textContent = `Successfully created workspace '${workspaceName}'`;
        return newWorkspace;
    }
    
    uploadMessage.textContent = 'Failed to create workspace';
    return null;
}

// Function to find a user by name (for search)
async function findUser(username) {
    workspaceMessage.textContent = `Looking for user '${username}'...`;
    workspaceMessage.className = '';
    
    const existingUser = await handleRequest(
        `http://localhost:8000/users/?username=${encodeURIComponent(username)}`,
        { method: 'GET' },
        'Failed to find user'
    );

    if (existingUser && existingUser.length > 0) {
        workspaceMessage.textContent = `Found user '${username}'`;
        return existingUser[0];
    }
    
    workspaceMessage.textContent = `User '${username}' not found`;
    return null;
}

// Function to find a workspace by name and user (for search)
async function findWorkspace(workspaceName, userId) {
    workspaceMessage.textContent = `Looking for workspace '${workspaceName}'...`;
    
    const existingWorkspace = await handleRequest(
        `http://localhost:8000/workspaces/?owner_id=${userId}&name=${encodeURIComponent(workspaceName)}`,
        { method: 'GET' },
        'Failed to find workspace'
    );

    if (existingWorkspace && existingWorkspace.length > 0) {
        workspaceMessage.textContent = `Found workspace '${workspaceName}'`;
        return existingWorkspace[0];
    }
    
    workspaceMessage.textContent = `Workspace '${workspaceName}' not found for this user`;
    return null;
}

// Search function
async function performSearch() {
    const query = document.getElementById('searchQuery').value;
    if (!query) {
        resultsDiv.innerHTML = 'Please enter a search query.';
        return;
    }
    if (!currentWorkspaceId) {
        resultsDiv.innerHTML = 'Please select a workspace first.';
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

// Workspace selection function
async function selectWorkspace() {
    const username = document.getElementById('searchUsername').value;
    const workspaceName = document.getElementById('searchWorkspace').value;

    if (!username || !workspaceName) {
        workspaceMessage.textContent = 'Please enter both username and workspace name.';
        return;
    }

    // Find the user
    const user = await findUser(username);
    if (!user) return;

    // Find the workspace for this user
    const workspace = await findWorkspace(workspaceName, user.id);
    if (!workspace) return;

    // Set the current workspace for searching
    currentWorkspaceId = workspace.id;
    workspaceMessage.textContent = `Selected workspace: ${workspaceName} (ID: ${workspace.id})`;
    
    // Show the search section
    searchSection.style.display = 'block';
    resultsDiv.innerHTML = ''; // Clear any previous results
}

// Main upload logic
uploadBtn.addEventListener('click', async () => {
    // 1. Get all necessary inputs
    const username = document.getElementById('uploadUsername').value;
    const workspaceName = document.getElementById('uploadWorkspace').value;
    const fileInput = document.getElementById('file');
    const files = fileInput.files;

    if (!username || !workspaceName || files.length === 0) {
        uploadMessage.textContent = 'Please fill in all fields and choose at least one file.';
        return;
    }

    // 2. Get or create the user
    const user = await getOrCreateUser(username);
    if (!user) return; // Stop if user creation failed

    // 3. Get or create the workspace
    const workspace = await getOrCreateWorkspace(workspaceName, user.id);
    if (!workspace) return; // Stop if workspace creation failed

    // 4. Upload the files sequentially
    for (let i = 0; i < files.length; i++) {
        const file = files[i];
        uploadMessage.textContent = `Uploading file ${i + 1} of ${files.length}: '${file.name}'...`;
        
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
            uploadMessage.textContent += ' Halting upload process.';
            return; // Stop the batch if any file fails
        }
    }
    
    uploadMessage.textContent = `Successfully uploaded all ${files.length} files!`;
});

// Event listeners
selectWorkspaceBtn.addEventListener('click', selectWorkspace);
searchBtn.addEventListener('click', performSearch); 