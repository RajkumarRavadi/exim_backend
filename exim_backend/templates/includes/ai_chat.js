// AI Chat Interface JavaScript
(function() {
	'use strict';

	// DOM Elements
	const chatMessages = document.getElementById('chatMessages');
	const messageInput = document.getElementById('messageInput');
	const sendBtn = document.getElementById('sendBtn');
	const uploadBtn = document.getElementById('uploadBtn');
	const fileInput = document.getElementById('fileInput');
	const imagePreview = document.getElementById('imagePreview');
	const previewImg = document.getElementById('previewImg');
	const removeImage = document.getElementById('removeImage');

	// State
	let currentImage = null;
	let isProcessing = false;
	let sessionId = localStorage.getItem('ai_chat_session_id') || generateSessionId();
	
	// Generate or retrieve session ID
	function generateSessionId() {
		const id = 'chat_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
		localStorage.setItem('ai_chat_session_id', id);
		return id;
	}

	// Initialize
	const init = () => {
		setupEventListeners();
		clearEmptyState();
	};

	// Event Listeners
	const setupEventListeners = () => {
		sendBtn.addEventListener('click', handleSendMessage);
		uploadBtn.addEventListener('click', () => fileInput.click());
		fileInput.addEventListener('change', handleImageUpload);
		removeImage.addEventListener('click', handleRemoveImage);
		
		// Clear history button
		const clearHistoryBtn = document.getElementById('clearHistoryBtn');
		if (clearHistoryBtn) {
			clearHistoryBtn.addEventListener('click', handleClearHistory);
		}
		
		messageInput.addEventListener('keydown', (e) => {
			if (e.key === 'Enter' && !e.shiftKey) {
				e.preventDefault();
				handleSendMessage();
			}
		});

		// Auto-resize textarea
		messageInput.addEventListener('input', () => {
			messageInput.style.height = 'auto';
			messageInput.style.height = messageInput.scrollHeight + 'px';
		});
	};

	// Clear empty state
	const clearEmptyState = () => {
		const emptyState = chatMessages.querySelector('.empty-state');
		if (emptyState && chatMessages.children.length > 1) {
			emptyState.remove();
		}
	};

	// Handle image upload
	const handleImageUpload = (e) => {
		const file = e.target.files[0];
		if (!file) return;

		// Validate file type
		if (!file.type.startsWith('image/')) {
			showError('Please upload a valid image file');
			return;
		}

		// Preview image
		const reader = new FileReader();
		reader.onload = (event) => {
			previewImg.src = event.target.result;
			imagePreview.classList.add('active');
			currentImage = file;
		};
		reader.readAsDataURL(file);
	};

	// Handle remove image
	const handleRemoveImage = () => {
		imagePreview.classList.remove('active');
		previewImg.src = '';
		currentImage = null;
		fileInput.value = '';
	};

	// Handle clear history
	const handleClearHistory = async () => {
		if (!confirm('Are you sure you want to clear the conversation history?')) {
			return;
		}

		try {
			const formData = new FormData();
			formData.append('session_id', sessionId);

			const response = await fetch('/api/method/exim_backend.api.ai_chat.clear_chat_history', {
				method: 'POST',
				headers: {
					'X-Frappe-CSRF-Token': getCSRFToken()
				},
				body: formData
			});

			if (!response.ok) {
				throw new Error(`HTTP error! status: ${response.status}`);
			}

			const result = await response.json();
			if (result.status === 'success' || (result.message && result.message.status === 'success')) {
				// Clear chat messages (keep empty state)
				chatMessages.innerHTML = `
					<div class="empty-state">
						<div class="empty-state-icon">💬</div>
						<h3>Welcome to AI Assistant</h3>
						<p>Send a message or upload an image to get started</p>
					</div>
				`;
				showSuccess('Conversation history cleared');
			} else {
				showError('Failed to clear history');
			}
		} catch (error) {
			console.error('Clear history error:', error);
			showError('Failed to clear history. Please try again.');
		}
	};

	// Handle send message
	const handleSendMessage = async () => {
		const message = messageInput.value.trim();

		// Validate input
		if (!message && !currentImage) {
			showError('Please enter a message or upload an image');
			return;
		}

		if (isProcessing) return;

		// Clear empty state
		const emptyState = chatMessages.querySelector('.empty-state');
		if (emptyState) {
			emptyState.remove();
		}

		// Add user message to chat
		if (message) {
			addMessage(message, 'user');
		}

		if (currentImage) {
			addImageMessage(currentImage, 'user');
		}

		// Clear input
		const messageToSend = message;
		const imageToSend = currentImage;
		messageInput.value = '';
		messageInput.style.height = 'auto';
		handleRemoveImage();

		// Show typing indicator
		showTypingIndicator();

		// Disable send button
		isProcessing = true;
		sendBtn.disabled = true;

		// Send to API
		try {
			const response = await sendChatMessage(messageToSend, imageToSend);
			hideTypingIndicator();

			// Log prompt information to browser console
			if (response.prompt_info) {
				console.log('%c═══════════════════════════════════════════════════════════════', 'color: #3b82f6; font-weight: bold; font-size: 14px;');
				console.log('%c📋 PROMPT SENT TO AI', 'color: #3b82f6; font-weight: bold; font-size: 16px;');
				console.log('%c═══════════════════════════════════════════════════════════════', 'color: #3b82f6; font-weight: bold; font-size: 14px;');
				
				const promptInfo = response.prompt_info;
				
				console.log('%c📊 Summary:', 'color: #10b981; font-weight: bold;');
				console.log({
					'Detected DocTypes': promptInfo.detected_doctypes,
					'Total Messages': promptInfo.total_messages,
					'History Count': promptInfo.history_count,
					'System Prompt Length': `${promptInfo.system_prompt_length} chars (${promptInfo.system_prompt_tokens} tokens)`
				});
				
				console.log('%c\n📝 System Prompt Preview:', 'color: #10b981; font-weight: bold;');
				console.log(promptInfo.system_prompt_preview);
				
				console.log('%c\n📋 Messages Summary:', 'color: #10b981; font-weight: bold;');
				promptInfo.messages_summary.forEach((msg, idx) => {
					console.log(`%c[${idx + 1}] ${msg.role.toUpperCase()}`, 'color: #f59e0b; font-weight: bold;', {
						'Content Preview': msg.content_preview,
						'Length': `${msg.content_length} chars`,
						'Tokens': msg.tokens
					});
				});
				
				console.log('%c\n📦 Full Messages Array:', 'color: #10b981; font-weight: bold;');
				console.log(promptInfo.full_messages);
				
				console.log('%c\n💾 Full Prompt Info Object:', 'color: #10b981; font-weight: bold;');
				console.log(promptInfo);
				
				console.log('%c═══════════════════════════════════════════════════════════════', 'color: #3b82f6; font-weight: bold; font-size: 14px;');
				console.log('%c✅ END OF PROMPT LOG', 'color: #3b82f6; font-weight: bold; font-size: 16px;');
				console.log('%c═══════════════════════════════════════════════════════════════', 'color: #3b82f6; font-weight: bold; font-size: 14px;');
			}

			console.log('API Response:', response);
			console.log('Suggested action:', response.suggested_action);
			console.log('Suggested action type:', typeof response.suggested_action);
			
			if (response.suggested_action) {
				console.log('Action details:', JSON.stringify(response.suggested_action, null, 2));
			}

			if (response.status === 'success') {
				// Remove JSON from AI message if suggested action exists
				let cleanMessage = response.message || '';
				
				// If there's a suggested action, remove ALL JSON from the message
				if (response.suggested_action) {
					// Remove any JSON objects (including nested ones)
					cleanMessage = cleanMessage.replace(/\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}/g, '').trim();
					// Remove any remaining JSON fragments
					cleanMessage = cleanMessage.replace(/["\s]*suggested_action["\s]*[:=]/gi, '').trim();
					cleanMessage = cleanMessage.replace(/["\s]*execute_immediately["\s]*[:=]/gi, '').trim();
					cleanMessage = cleanMessage.replace(/["\s]*confidence["\s]*[:=]/gi, '').trim();
					cleanMessage = cleanMessage.replace(/["\s]*action["\s]*[:=]/gi, '').trim();
					cleanMessage = cleanMessage.replace(/["\s]*filters["\s]*[:=]/gi, '').trim();
					cleanMessage = cleanMessage.replace(/[{},":\[\]]/g, ' ').replace(/\s+/g, ' ').trim();
					
					// If message is now empty or just contains JSON remnants, use a default message
					if (!cleanMessage || cleanMessage.length < 5 || cleanMessage.match(/^[\s\w]*$/i)) {
						const action = response.suggested_action.action;
						if (action === 'dynamic_search') {
							cleanMessage = 'Searching for customers...';
						} else if (action === 'search_customer') {
							cleanMessage = `Searching for customer: ${response.suggested_action.query || ''}`;
						} else if (action === 'get_customer_details') {
							cleanMessage = `Fetching details for: ${response.suggested_action.customer_name || ''}`;
						} else if (action === 'create_document') {
							cleanMessage = `Ready to create a ${response.suggested_action.doctype || 'document'}`;
						} else if (action === 'count_customers') {
							cleanMessage = 'Counting customers...';
						} else if (action === 'find_duplicates') {
							cleanMessage = 'Checking for duplicate customer names...';
						} else {
							cleanMessage = 'Processing your request...';
						}
					}
				}
				
				// Remove code block markers if still present
				if (cleanMessage.includes('```')) {
					cleanMessage = cleanMessage.replace(/```json\s*/g, '').replace(/```\s*/g, '').trim();
				}
				
				// Final cleanup - remove any remaining special characters that look like JSON
				cleanMessage = cleanMessage.replace(/^[,\s}]+|[,\s{]+$/g, '').trim();
				
				console.log('Clean message:', cleanMessage);
				console.log('Passing suggested_action:', response.suggested_action);
				
				// Display token usage if available
				if (response.token_usage) {
					console.log('Token usage:', response.token_usage);
					const tokenInfo = `📊 Tokens: ${response.token_usage.input_tokens} in + ${response.token_usage.output_tokens} out = ${response.token_usage.total_tokens} total`;
					console.log(tokenInfo);
				}
				
				// Check if action should be executed immediately
				if (response.suggested_action && response.suggested_action.execute_immediately) {
					console.log('Auto-executing action:', response.suggested_action.action);
					// Don't show the message if it's just JSON remnants - let the action handler show results
					if (cleanMessage && cleanMessage.length > 5 && !cleanMessage.match(/^[\s\w]*$/i)) {
						addMessage(`<p>${escapeHtml(cleanMessage)}</p>`, 'ai', null, response.token_usage);
					}
					autoExecuteAction(response.suggested_action);
				} else {
					addMessage(`<p>${escapeHtml(cleanMessage)}</p>`, 'ai', response.suggested_action, response.token_usage);
				}
			} else {
				showError(response.message || 'An error occurred');
			}
		} catch (error) {
			hideTypingIndicator();
			showError('Failed to send message. Please try again.');
			console.error('Chat error:', error);
		} finally {
			isProcessing = false;
			sendBtn.disabled = false;
		}
	};

	// Get CSRF token
	const getCSRFToken = () => {
		let token = '';
		
		// Try getting from frappe object
		if (typeof frappe !== 'undefined' && frappe.csrf_token) {
			token = frappe.csrf_token;
			console.log('CSRF token from frappe object:', token);
		}
		// Try getting from meta tag
		else {
			const metaTag = document.querySelector('meta[name="csrf-token"]');
			if (metaTag) {
				token = metaTag.getAttribute('content');
				console.log('CSRF token from meta tag:', token);
			}
		}
		
		if (!token) {
			console.warn('WARNING: No CSRF token found! This will cause 400 errors.');
		}
		
		return token;
	};

	// Send message to API
	const sendChatMessage = async (message, image) => {
		const formData = new FormData();
		formData.append('message', message);
		formData.append('session_id', sessionId);
		
		if (image) {
			formData.append('image', image);
		}

		const response = await fetch('/api/method/exim_backend.api.ai_chat.process_chat', {
			method: 'POST',
			headers: {
				'X-Frappe-CSRF-Token': getCSRFToken()
			},
			body: formData
		});

		if (!response.ok) {
			const errorText = await response.text();
			console.error('API Error:', errorText);
			throw new Error(`HTTP error! status: ${response.status}`);
		}

		const result = await response.json();
		// Frappe wraps the response in a 'message' key
		return result.message || result;
	};

	// Escape HTML to prevent XSS
	const escapeHtml = (text) => {
		const div = document.createElement('div');
		div.textContent = text;
		return div.innerHTML;
	};

	// Add message to chat
	const addMessage = (content, sender, suggestedAction = null, tokenUsage = null) => {
		const messageDiv = document.createElement('div');
		messageDiv.className = `message ${sender}`;

		const avatar = document.createElement('div');
		avatar.className = 'message-avatar';
		avatar.textContent = sender === 'user' ? 'U' : '🤖';

		const messageContent = document.createElement('div');
		messageContent.className = 'message-content';
		
		// Use innerHTML to support HTML formatting, but escape for user messages
		if (sender === 'user') {
			messageContent.textContent = content;
		} else {
			// For AI messages, allow HTML formatting
			messageContent.innerHTML = content;
			
			// Add token usage display if available
			if (tokenUsage) {
				const tokenDiv = document.createElement('div');
				tokenDiv.style.cssText = 'margin-top: 8px; font-size: 11px; color: #9ca3af; font-style: italic;';
				tokenDiv.textContent = `📊 ${tokenUsage.input_tokens} in + ${tokenUsage.output_tokens} out = ${tokenUsage.total_tokens} tokens`;
				messageContent.appendChild(tokenDiv);
			}
		}

		messageDiv.appendChild(avatar);
		messageDiv.appendChild(messageContent);

		// Add suggested action if present
		if (suggestedAction && suggestedAction.action) {
			console.log('Creating action element for:', suggestedAction.action);
			const actionDiv = createSuggestedActionElement(suggestedAction);
			if (actionDiv) {
				messageContent.appendChild(actionDiv);
			}
		}

		chatMessages.appendChild(messageDiv);
		scrollToBottom();
	};

	// Add image message
	const addImageMessage = (file, sender) => {
		const messageDiv = document.createElement('div');
		messageDiv.className = `message ${sender}`;

		const avatar = document.createElement('div');
		avatar.className = 'message-avatar';
		avatar.textContent = sender === 'user' ? 'U' : '🤖';

		const messageContent = document.createElement('div');
		messageContent.className = 'message-content';

		const img = document.createElement('img');
		img.style.maxWidth = '200px';
		img.style.borderRadius = '8px';
		
		const reader = new FileReader();
		reader.onload = (e) => {
			img.src = e.target.result;
		};
		reader.readAsDataURL(file);

		messageContent.appendChild(img);
		messageDiv.appendChild(avatar);
		messageDiv.appendChild(messageContent);

		chatMessages.appendChild(messageDiv);
		scrollToBottom();
	};

	// Create suggested action element
	const createSuggestedActionElement = (action) => {
		// Don't create button if should execute immediately
		if (action.execute_immediately) {
			return null;
		}

		const actionDiv = document.createElement('div');
		actionDiv.className = 'suggested-action';

		// Handle different action types
		if (action.action === 'create_document') {
			const title = document.createElement('h4');
			title.textContent = `Suggested: Create ${action.doctype}`;

			const fieldsText = document.createElement('p');
			fieldsText.style.margin = '0';
			fieldsText.style.fontSize = '13px';
			fieldsText.style.color = '#4a5568';
			fieldsText.textContent = `Fields: ${Object.keys(action.fields || {}).join(', ')}`;

			const buttonContainer = document.createElement('div');
			buttonContainer.className = 'suggested-action-buttons';

			const createBtn = document.createElement('button');
			createBtn.className = 'btn-action btn-action-primary';
			createBtn.textContent = 'Create Document';
			createBtn.onclick = () => handleCreateDocument(action);

			const cancelBtn = document.createElement('button');
			cancelBtn.className = 'btn-action btn-action-secondary';
			cancelBtn.textContent = 'Cancel';
			cancelBtn.onclick = () => actionDiv.remove();

			buttonContainer.appendChild(createBtn);
			buttonContainer.appendChild(cancelBtn);

			actionDiv.appendChild(title);
			actionDiv.appendChild(fieldsText);
			actionDiv.appendChild(buttonContainer);
			
		} else if (action.action === 'search_customer') {
			const title = document.createElement('h4');
			title.textContent = `Search for: ${action.query}`;

			const buttonContainer = document.createElement('div');
			buttonContainer.className = 'suggested-action-buttons';

			const searchBtn = document.createElement('button');
			searchBtn.className = 'btn-action btn-action-primary';
			searchBtn.textContent = 'Search';
			searchBtn.onclick = () => handleSearchCustomer(action);

			const cancelBtn = document.createElement('button');
			cancelBtn.className = 'btn-action btn-action-secondary';
			cancelBtn.textContent = 'Cancel';
			cancelBtn.onclick = () => actionDiv.remove();

			buttonContainer.appendChild(searchBtn);
			buttonContainer.appendChild(cancelBtn);

			actionDiv.appendChild(title);
			actionDiv.appendChild(buttonContainer);
			
		} else if (action.action === 'get_customer_details') {
			const title = document.createElement('h4');
			title.textContent = `Get details: ${action.customer_name}`;

			const buttonContainer = document.createElement('div');
			buttonContainer.className = 'suggested-action-buttons';

			const detailsBtn = document.createElement('button');
			detailsBtn.className = 'btn-action btn-action-primary';
			detailsBtn.textContent = 'Show Details';
			detailsBtn.onclick = () => handleGetCustomerDetails(action);

			const cancelBtn = document.createElement('button');
			cancelBtn.className = 'btn-action btn-action-secondary';
			cancelBtn.textContent = 'Cancel';
			cancelBtn.onclick = () => actionDiv.remove();

			buttonContainer.appendChild(detailsBtn);
			buttonContainer.appendChild(cancelBtn);

			actionDiv.appendChild(title);
			actionDiv.appendChild(buttonContainer);
		}

		return actionDiv;
	};

	// Handle create document
	const handleCreateDocument = async (action) => {
		try {
			showTypingIndicator();

			const formData = new FormData();
			formData.append('doctype', action.doctype);
			formData.append('fields', JSON.stringify(action.fields));

			const response = await fetch('/api/method/exim_backend.api.ai_chat.create_document', {
				method: 'POST',
				headers: {
					'X-Frappe-CSRF-Token': getCSRFToken()
				},
				body: formData
			});

			if (!response.ok) {
				const errorText = await response.text();
				console.error('API Error:', errorText);
				throw new Error(`HTTP error! status: ${response.status}`);
			}

			const responseData = await response.json();
			console.log('Create document - Raw response:', responseData);
			
			// Frappe wraps the response in a 'message' key
			const result = responseData.message || responseData;
			console.log('Create document - Parsed result:', result);
			
			hideTypingIndicator();

			if (result && result.status === 'success') {
				// Build document link from name and doctype
				const doctype = result.doctype || action.doctype || 'Customer';
				const docName = result.name || (result.document && result.document.name);
				
				console.log('Create document - Extracted info:', { doctype, docName, result });
				
				let linkText = '';
				if (docName) {
					// Construct ERPNext document URL
					const docUrl = `/app/${doctype.toLowerCase().replace(/\s+/g, '-')}/${encodeURIComponent(docName)}`;
					linkText = `\n\n🔗 <a href="${docUrl}" target="_blank" style="color: #3b82f6; text-decoration: none;">View ${doctype} →</a>`;
				} else {
					linkText = `\n\n📄 Document created successfully`;
				}
				
				const successMessage = result.message || `✅ ${doctype} created successfully`;
				addMessage(`${successMessage}${linkText}`, 'ai');
				
				// Show success notification
				console.log('✅ Document created successfully:', { doctype, name: docName, result });
			} else {
				// Handle error response
				const errorMessage = result?.message || result?.error || 'Unknown error occurred';
				console.error('❌ Create document failed:', result);
				addMessage(`❌ Error: ${errorMessage}`, 'ai');
			}
		} catch (error) {
			hideTypingIndicator();
			console.error('Create document error:', error);
			console.error('Error stack:', error.stack);
			
			// Show more detailed error message
			const errorMsg = error.message || 'Failed to create document. Please try again.';
			addMessage(`❌ Error: ${errorMsg}`, 'ai');
			showError(errorMsg);
		}
	};

	// Auto-execute action
	const autoExecuteAction = (action) => {
		console.log('Auto-executing:', action);
		const doctype = action.doctype || 'Customer'; // Default to Customer for backward compatibility
		
		if (action.action === 'dynamic_search') {
			handleDynamicSearch(action);
		} else if (action.action === 'get_document_details' || action.action === 'get_customer_details') {
			handleGetDocumentDetails(action);
		} else if (action.action === 'find_duplicates' || action.action === 'find_duplicate_customers') {
			handleFindDuplicates(action);
		} else if (action.action === 'count_documents' || action.action === 'count_customers') {
			handleCountDocuments(action);
		} else if (action.action === 'search_customer') {
			// Legacy support
			handleSearchCustomer(action);
		}
	};

	// Handle find duplicates
	const handleFindDuplicates = async (action) => {
		try {
			showTypingIndicator();
			const doctype = action?.doctype || 'Customer';
			
			const formData = new FormData();
			formData.append('doctype', doctype);

			const response = await fetch('/api/method/exim_backend.api.ai_chat.find_duplicates', {
				method: 'POST',
				headers: {
					'X-Frappe-CSRF-Token': getCSRFToken()
				},
				body: formData
			});

			if (!response.ok) {
				throw new Error(`HTTP error! status: ${response.status}`);
			}

			const responseData = await response.json();
			const result = responseData.message || responseData;

			hideTypingIndicator();

			if (result.status === 'success') {
				displayDuplicateResults(result);
			} else {
				addMessage(`⚠️ Failed to find duplicates: ${result.message}`, 'ai');
			}
		} catch (error) {
			hideTypingIndicator();
			addMessage('❌ Error finding duplicates. Please try again.', 'ai');
			console.error('Find duplicates error:', error);
		}
	};

	// Display duplicate results
	const displayDuplicateResults = (result) => {
		console.log('🔍 Duplicate Results:', result);

		let message = '';

		if (result.duplicate_count === 0) {
			message = '<p>✅ Great! All customer names are unique. No duplicates found.</p>';
		} else {
			if (result.duplicate_count === 1) {
				message = `<p>⚠️ I found <strong>${result.duplicate_count} customer name</strong> that appears multiple times:</p>`;
			} else {
				message = `<p>⚠️ I found <strong>${result.duplicate_count} customer names</strong> that appear multiple times:</p>`;
			}

			message += '<div style="margin-top: 12px;">';
			result.duplicates.forEach((dup, index) => {
				message += `<div style="margin-bottom: 16px; padding-bottom: 12px; border-bottom: 1px solid #e5e7eb;">`;
				message += `<div style="font-weight: 600; font-size: 15px; color: #1f2937; margin-bottom: 8px;">"${escapeHtml(dup.customer_name)}" appears ${dup.count} times:</div>`;
				
				dup.customers.forEach((customer, idx) => {
					const customerUrl = `${window.location.origin}/app/customer/${encodeURIComponent(customer.name)}`;
					const details = [];
					if (customer.mobile_no) details.push(`Phone: ${escapeHtml(customer.mobile_no)}`);
					if (customer.email_id) details.push(`Email: ${escapeHtml(customer.email_id)}`);
					
					message += `<div style="margin-bottom: 8px; padding-left: 12px;">`;
					message += `<span style="color: #4b5563;">${idx + 1}. ${escapeHtml(customer.name)}</span>`;
					if (details.length > 0) {
						message += ` <span style="color: #6b7280; font-size: 13px;">(${details.join(', ')})</span>`;
					}
					message += `<br><a href="${customerUrl}" target="_blank" style="color: #3b82f6; text-decoration: none; font-size: 13px; margin-left: 12px;">View →</a>`;
					message += `</div>`;
				});
				message += `</div>`;
			});
			message += '</div>';
		}

		addMessage(message, 'ai');
	};

	// Handle count documents
	const handleCountDocuments = async (action) => {
		try {
			showTypingIndicator();
			const doctype = action?.doctype || 'Customer';
			
			const formData = new FormData();
			formData.append('doctype', doctype);
			if (action?.filters) {
				formData.append('filters', JSON.stringify(action.filters));
			}

			const response = await fetch('/api/method/exim_backend.api.ai_chat.count_documents', {
				method: 'POST',
				headers: {
					'X-Frappe-CSRF-Token': getCSRFToken()
				},
				body: formData
			});

			if (!response.ok) {
				throw new Error(`HTTP error! status: ${response.status}`);
			}

			const responseData = await response.json();
			const result = responseData.message || responseData;
			hideTypingIndicator();

			if (result.status === 'success') {
				displayCustomerCount(result, doctype);
			} else {
				addMessage(`❌ ${result.message}`, 'ai');
			}
		} catch (error) {
			hideTypingIndicator();
			showError(`Failed to count ${doctype.toLowerCase()}s. Please try again.`);
			console.error('Count error:', error);
		}
	};

	// Legacy handler for backward compatibility
	const handleCountCustomers = async () => {
		return handleCountDocuments({ doctype: 'Customer' });
	};

	// Display customer count
	const displayCustomerCount = (result, doctype = 'Customer') => {
		const doctypeLabel = doctype.toLowerCase() + (doctype.toLowerCase().endsWith('s') ? '' : 's');
		let message = `<p>You have <strong>${result.total_count} ${doctypeLabel}</strong> in total.</p>`;

		if (result.by_territory && result.by_territory.length > 0) {
			message += `<div style="margin-top: 12px;"><strong style="color: #1f2937;">By Territory:</strong><ul style="margin: 8px 0 0 20px; padding: 0; color: #4b5563;">`;
			result.by_territory.forEach(item => {
				message += `<li style="margin-bottom: 4px;">${escapeHtml(item.territory)}: ${item.count}</li>`;
			});
			message += `</ul></div>`;
		}

		if (result.by_group && result.by_group.length > 0) {
			message += `<div style="margin-top: 12px;"><strong style="color: #1f2937;">By Customer Group:</strong><ul style="margin: 8px 0 0 20px; padding: 0; color: #4b5563;">`;
			result.by_group.forEach(item => {
				message += `<li style="margin-bottom: 4px;">${escapeHtml(item.customer_group)}: ${item.count}</li>`;
			});
			message += `</ul></div>`;
		}

		addMessage(message, 'ai');
	};

	// Handle dynamic search with filters
	const handleDynamicSearch = async (action) => {
		try {
			showTypingIndicator();
			const doctype = action?.doctype || 'Customer';

			const formData = new FormData();
			formData.append('doctype', doctype);
			formData.append('filters', JSON.stringify(action.filters));
			formData.append('limit', action?.limit || '20');

			const response = await fetch('/api/method/exim_backend.api.ai_chat.dynamic_search', {
				method: 'POST',
				headers: {
					'X-Frappe-CSRF-Token': getCSRFToken()
				},
				body: formData
			});

			if (!response.ok) {
				throw new Error(`HTTP error! status: ${response.status}`);
			}

			const responseData = await response.json();
			const result = responseData.message || responseData;

			hideTypingIndicator();

			if (result.status === 'success') {
				displayDynamicSearchResults(result);
			} else {
				addMessage(`⚠️ Search failed: ${result.message}`, 'ai');
			}
		} catch (error) {
			hideTypingIndicator();
			addMessage('❌ Search error. Please try again.', 'ai');
			console.error('Dynamic search error:', error);
		}
	};

	// Display dynamic search results
	const displayDynamicSearchResults = (result) => {
		// Log filters to console for debugging (not shown to user)
		if (result.filters_applied && Object.keys(result.filters_applied).length > 0) {
			console.log('🔍 Filters Applied:', result.filters_applied);
		}

		let message = '';

		if (result.count > 0) {
			// Friendly introduction
			if (result.count === 1) {
				message += `<p>I found <strong>${result.count} customer</strong> matching your search:</p>`;
			} else {
				message += `<p>I found <strong>${result.count} customers</strong> matching your search:</p>`;
			}

			// Display customers in a clean, readable format
			message += '<div style="margin-top: 12px;">';
			result.customers.forEach((customer, index) => {
				const customerName = customer.customer_name || customer.name;
				const customerUrl = `${window.location.origin}/app/customer/${encodeURIComponent(customer.name)}`;
				
				message += `<div style="margin-bottom: 16px; padding-bottom: 12px; border-bottom: 1px solid #e5e7eb;">`;
				message += `<div style="font-weight: 600; font-size: 15px; color: #1f2937; margin-bottom: 6px;">${escapeHtml(customerName)}</div>`;
				
				// Build info line with available details
				const details = [];
				if (customer.mobile_no) details.push(`<span style="color: #4b5563;">Phone: ${escapeHtml(customer.mobile_no)}</span>`);
				if (customer.email_id) details.push(`<span style="color: #4b5563;">Email: ${escapeHtml(customer.email_id)}</span>`);
				if (customer.territory) details.push(`<span style="color: #4b5563;">Territory: ${escapeHtml(customer.territory)}</span>`);
				if (customer.customer_group) details.push(`<span style="color: #4b5563;">Group: ${escapeHtml(customer.customer_group)}</span>`);
				if (customer.default_currency) details.push(`<span style="color: #4b5563;">Currency: ${escapeHtml(customer.default_currency)}</span>`);
				
				if (details.length > 0) {
					message += `<div style="font-size: 13px; margin-bottom: 8px; line-height: 1.5;">${details.join(' <span style="color: #9ca3af;">•</span> ')}</div>`;
				}
				
				message += `<a href="${customerUrl}" target="_blank" style="color: #3b82f6; text-decoration: none; font-size: 13px; font-weight: 500;">View Customer →</a>`;
				message += `</div>`;
			});
			message += '</div>';
		} else {
			message = `<p>I couldn't find any customers matching your search criteria.</p><p style="margin-top: 8px; color: #6b7280;">💡 Try adjusting your search terms or filters.</p>`;
		}

		addMessage(message, 'ai');
	};

	// Handle search customer
	const handleSearchCustomer = async (action) => {
		try {
			showTypingIndicator();

			const formData = new FormData();
			formData.append('query', action.query);
			formData.append('limit', '10');

			const response = await fetch('/api/method/exim_backend.api.ai_chat.search_customers', {
				method: 'POST',
				headers: {
					'X-Frappe-CSRF-Token': getCSRFToken()
				},
				body: formData
			});

			if (!response.ok) {
				throw new Error(`HTTP error! status: ${response.status}`);
			}

			const responseData = await response.json();
			const result = responseData.message || responseData;
			hideTypingIndicator();

			if (result.status === 'success') {
				displayCustomerSearchResults(result);
			} else {
				addMessage(`❌ Search failed: ${result.message}`, 'ai');
			}
		} catch (error) {
			hideTypingIndicator();
			showError('Failed to search customers. Please try again.');
			console.error('Search error:', error);
		}
	};

	// Display customer search results
	const displayCustomerSearchResults = (result) => {
		if (result.count === 0) {
			addMessage('<p>I couldn\'t find any customers matching your search. Try different keywords.</p>', 'ai');
			return;
		}

		let message = '';
		if (result.count === 1) {
			message += `<p>I found <strong>${result.count} customer</strong>:</p>`;
		} else {
			message += `<p>I found <strong>${result.count} customers</strong>:</p>`;
		}
		
		message += '<div style="margin-top: 12px;">';
		result.customers.forEach((customer, index) => {
			const customerUrl = `${window.location.origin}/app/customer/${encodeURIComponent(customer.name)}`;
			
			message += `<div style="margin-bottom: 16px; padding-bottom: 12px; border-bottom: 1px solid #e5e7eb;">`;
			message += `<div style="font-weight: 600; font-size: 15px; color: #1f2937; margin-bottom: 6px;">${escapeHtml(customer.customer_name)}</div>`;
			
			const details = [];
			if (customer.mobile_no) details.push(`<span style="color: #4b5563;">Phone: ${escapeHtml(customer.mobile_no)}</span>`);
			if (customer.email_id) details.push(`<span style="color: #4b5563;">Email: ${escapeHtml(customer.email_id)}</span>`);
			if (customer.territory) details.push(`<span style="color: #4b5563;">Territory: ${escapeHtml(customer.territory)}</span>`);
			if (customer.default_currency) details.push(`<span style="color: #4b5563;">Currency: ${escapeHtml(customer.default_currency)}</span>`);
			
			if (details.length > 0) {
				message += `<div style="font-size: 13px; margin-bottom: 8px; line-height: 1.5;">${details.join(' <span style="color: #9ca3af;">•</span> ')}</div>`;
			}
			
			message += `<a href="${customerUrl}" target="_blank" style="color: #3b82f6; text-decoration: none; font-size: 13px; font-weight: 500;">View Customer →</a>`;
			message += `</div>`;
		});
		message += '</div>';

		addMessage(message, 'ai');
	};

	// Handle get customer details
	const handleGetDocumentDetails = async (action) => {
		try {
			showTypingIndicator();
			const doctype = action?.doctype || 'Customer';
			const name = action?.name || action?.customer_name; // Support both formats

			if (!name) {
				throw new Error('Document name is required');
			}

			const formData = new FormData();
			formData.append('doctype', doctype);
			formData.append('name', name);

			const response = await fetch('/api/method/exim_backend.api.ai_chat.get_document_details', {
				method: 'POST',
				headers: {
					'X-Frappe-CSRF-Token': getCSRFToken()
				},
				body: formData
			});

			if (!response.ok) {
				throw new Error(`HTTP error! status: ${response.status}`);
			}

			const responseData = await response.json();
			const result = responseData.message || responseData;
			hideTypingIndicator();

			if (result.status === 'success') {
				// Support both customer and generic document formats
				const document = result.customer || result.document;
				if (doctype === 'Customer') {
					displayCustomerDetails(document);
				} else {
					// Generic display for other doctypes
					displayDocumentDetails(document, doctype);
				}
			} else {
				addMessage(`❌ ${result.message}`, 'ai');
			}
		} catch (error) {
			hideTypingIndicator();
			showError('Failed to get document details. Please try again.');
			console.error('Get details error:', error);
		}
	};

	// Legacy handler for backward compatibility
	const handleGetCustomerDetails = async (action) => {
		action.doctype = 'Customer';
		return handleGetDocumentDetails(action);
	};

	// Display customer details
	const displayCustomerDetails = (customer) => {
		const customerUrl = `${window.location.origin}/app/customer/${encodeURIComponent(customer.name)}`;
		let message = `<p>Here are the details for <strong>${escapeHtml(customer.customer_name)}</strong>:</p>`;
		
		message += '<div style="margin-top: 12px;">';
		
		// Contact Information
		const contactInfo = [];
		if (customer.mobile_no) contactInfo.push(`<span style="color: #4b5563;">📱 ${escapeHtml(customer.mobile_no)}</span>`);
		if (customer.email_id) contactInfo.push(`<span style="color: #4b5563;">📧 ${escapeHtml(customer.email_id)}</span>`);
		if (contactInfo.length > 0) {
			message += `<div style="margin-bottom: 12px; font-size: 14px; line-height: 1.6;">${contactInfo.join(' <span style="color: #9ca3af;">•</span> ')}</div>`;
		}
		
		// Business Information
		const businessInfo = [];
		if (customer.customer_type) businessInfo.push(`<span style="color: #4b5563;">Type: ${escapeHtml(customer.customer_type)}</span>`);
		if (customer.customer_group) businessInfo.push(`<span style="color: #4b5563;">Group: ${escapeHtml(customer.customer_group)}</span>`);
		if (customer.territory) businessInfo.push(`<span style="color: #4b5563;">Territory: ${escapeHtml(customer.territory)}</span>`);
		if (businessInfo.length > 0) {
			message += `<div style="margin-bottom: 12px; font-size: 14px; line-height: 1.6;">${businessInfo.join(' <span style="color: #9ca3af;">•</span> ')}</div>`;
		}
		
		// Financial Information
		const financialInfo = [];
		if (customer.default_currency) financialInfo.push(`<span style="color: #4b5563;">Currency: ${escapeHtml(customer.default_currency)}</span>`);
		if (customer.default_price_list) financialInfo.push(`<span style="color: #4b5563;">Price List: ${escapeHtml(customer.default_price_list)}</span>`);
		if (customer.payment_terms) financialInfo.push(`<span style="color: #4b5563;">Payment Terms: ${escapeHtml(customer.payment_terms)}</span>`);
		if (financialInfo.length > 0) {
			message += `<div style="margin-bottom: 12px; font-size: 14px; line-height: 1.6;">${financialInfo.join(' <span style="color: #9ca3af;">•</span> ')}</div>`;
		}
		
		// Primary Contact
		if (customer.customer_primary_contact) {
			message += `<div style="margin-bottom: 12px; font-size: 14px;"><span style="color: #4b5563;">Primary Contact: ${escapeHtml(customer.customer_primary_contact)}</span></div>`;
		}

		// Address
		if (customer.address) {
			const addressParts = [];
			if (customer.address.address_line1) addressParts.push(escapeHtml(customer.address.address_line1));
			if (customer.address.address_line2) addressParts.push(escapeHtml(customer.address.address_line2));
			if (customer.address.city) addressParts.push(escapeHtml(customer.address.city));
			if (customer.address.state) addressParts.push(escapeHtml(customer.address.state));
			if (customer.address.country) addressParts.push(escapeHtml(customer.address.country));
			if (customer.address.pincode) addressParts.push(escapeHtml(customer.address.pincode));
			
			if (addressParts.length > 0) {
				message += `<div style="margin-bottom: 12px; font-size: 14px;"><span style="color: #4b5563;">📍 Address: ${addressParts.join(', ')}</span></div>`;
			}
		}

		// Sales Team
		if (customer.sales_team && customer.sales_team.length > 0) {
			message += `<div style="margin-bottom: 12px; font-size: 14px;"><span style="color: #4b5563; font-weight: 500;">Sales Team:</span><ul style="margin: 6px 0 0 20px; padding: 0; color: #4b5563;">`;
			customer.sales_team.forEach(member => {
				let memberText = escapeHtml(member.sales_person);
				if (member.allocated_percentage) {
					memberText += ` (${member.allocated_percentage}%)`;
				}
				message += `<li style="margin-bottom: 4px;">${memberText}</li>`;
			});
			message += `</ul></div>`;
		}

		message += `<div style="margin-top: 12px;"><a href="${customerUrl}" target="_blank" style="color: #3b82f6; text-decoration: none; font-size: 13px; font-weight: 500;">View Customer →</a></div>`;
		message += '</div>';

		addMessage(message, 'ai');
	};

	// Display generic document details
	const displayDocumentDetails = (document, doctype) => {
		const docUrl = `${window.location.origin}/app/${doctype.toLowerCase().replace(/\s+/g, '-')}/${encodeURIComponent(document.name)}`;
		const nameField = document.name || document[`${doctype.toLowerCase()}_name`] || document.name;
		
		let message = `<p>Here are the details for <strong>${escapeHtml(nameField)}</strong>:</p>`;
		message += '<div style="margin-top: 12px;">';
		
		// Display key fields
		const fieldsToShow = Object.keys(document).filter(key => 
			!['name', 'doctype', 'creation', 'modified', 'modified_by', 'owner'].includes(key) &&
			document[key] !== null && 
			document[key] !== '' &&
			typeof document[key] !== 'object'
		).slice(0, 10); // Limit to first 10 fields
		
		fieldsToShow.forEach(field => {
			const value = document[field];
			if (value) {
				message += `<div style="margin-bottom: 8px; font-size: 14px;"><span style="color: #6b7280; font-weight: 500;">${escapeHtml(field.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()))}:</span> <span style="color: #1f2937;">${escapeHtml(String(value))}</span></div>`;
			}
		});
		
		message += `<div style="margin-top: 12px;"><a href="${docUrl}" target="_blank" style="color: #3b82f6; text-decoration: none; font-size: 13px; font-weight: 500;">View ${doctype} →</a></div>`;
		message += '</div>';
		
		addMessage(message, 'ai');
	};

	// Show typing indicator
	const showTypingIndicator = () => {
		const indicator = document.createElement('div');
		indicator.className = 'message ai';
		indicator.id = 'typingIndicator';

		const avatar = document.createElement('div');
		avatar.className = 'message-avatar';
		avatar.textContent = '🤖';

		const typingDiv = document.createElement('div');
		typingDiv.className = 'typing-indicator active';
		
		for (let i = 0; i < 3; i++) {
			const dot = document.createElement('div');
			dot.className = 'typing-dot';
			typingDiv.appendChild(dot);
		}

		indicator.appendChild(avatar);
		indicator.appendChild(typingDiv);
		chatMessages.appendChild(indicator);
		scrollToBottom();
	};

	// Hide typing indicator
	const hideTypingIndicator = () => {
		const indicator = document.getElementById('typingIndicator');
		if (indicator) {
			indicator.remove();
		}
	};

	// Show error message
	const showError = (message) => {
		addMessage(`❌ Error: ${message}`, 'ai');
	};

	const showSuccess = (message) => {
		// Show temporary success message
		const successDiv = document.createElement('div');
		successDiv.style.cssText = 'position: fixed; top: 20px; right: 20px; background: #48bb78; color: white; padding: 12px 20px; border-radius: 8px; z-index: 10000; box-shadow: 0 4px 6px rgba(0,0,0,0.1);';
		successDiv.textContent = `✅ ${message}`;
		document.body.appendChild(successDiv);
		setTimeout(() => successDiv.remove(), 3000);
	};

	// Scroll to bottom
	const scrollToBottom = () => {
		chatMessages.scrollTop = chatMessages.scrollHeight;
	};

	// Initialize when DOM is ready
	if (document.readyState === 'loading') {
		document.addEventListener('DOMContentLoaded', init);
	} else {
		init();
	}
})();

