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
					// Don't show the message if it contains phrases indicating the AI can't do something
					// or if it's asking the user to do something (since we'll do it automatically)
					const skipMessage = cleanMessage && (
						cleanMessage.toLowerCase().includes("i cannot") ||
						cleanMessage.toLowerCase().includes("i need") ||
						cleanMessage.toLowerCase().includes("please provide") ||
						cleanMessage.toLowerCase().includes("could you") ||
						cleanMessage.toLowerCase().includes("if you give me") ||
						cleanMessage.toLowerCase().includes("however if you") ||
						cleanMessage.match(/^[\s\w]*$/i) // Just whitespace/words (likely JSON remnants)
					);
					
					if (!skipMessage && cleanMessage && cleanMessage.length > 5) {
						addMessage(`<p>${escapeHtml(cleanMessage)}</p>`, 'ai', null, response.token_usage);
					}
					// Pass the original user message for context
					autoExecuteAction(response.suggested_action, message);
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
	// Store the original user question for context
	let lastUserQuestion = '';
	
	const autoExecuteAction = (action, originalQuestion = '') => {
		console.log('Auto-executing:', action);
		if (originalQuestion) {
			lastUserQuestion = originalQuestion;
		}
		const doctype = action.doctype || 'Customer'; // Default to Customer for backward compatibility
		
		if (action.action === 'dynamic_search') {
			handleDynamicSearch(action);
		} else if (action.action === 'get_document_details' || action.action === 'get_customer_details') {
			handleGetDocumentDetails(action, lastUserQuestion);
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
				displayDynamicSearchResults(result, doctype);
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
	const displayDynamicSearchResults = (result, doctype = null) => {
		// Log filters to console for debugging (not shown to user)
		if (result.filters_applied && Object.keys(result.filters_applied).length > 0) {
			console.log('🔍 Filters Applied:', result.filters_applied);
		}

		// Detect doctype from result keys (customers, items, etc.)
		let detectedDoctype = doctype;
		let resultsKey = null;
		let results = [];
		
		// Find the results array (could be customers, items, etc.)
		for (const key in result) {
			if (Array.isArray(result[key]) && key !== 'filters_applied') {
				resultsKey = key;
				results = result[key];
				// Infer doctype from key (customers -> Customer, items -> Item)
				if (!detectedDoctype) {
					detectedDoctype = key.charAt(0).toUpperCase() + key.slice(1, -1); // Remove 's' and capitalize
				}
				break;
			}
		}
		
		// Fallback to count if no array found
		if (!results.length && result.count) {
			results = result.results || [];
		}
		
		const doctypeLabel = detectedDoctype ? detectedDoctype.toLowerCase() + (result.count !== 1 ? 's' : '') : 'items';
		const doctypeSingular = detectedDoctype ? detectedDoctype.toLowerCase() : 'item';

		let message = '';

		if (result.count > 0 && results.length > 0) {
			// Friendly introduction
			if (result.count === 1) {
				message += `<p>I found <strong>${result.count} ${doctypeSingular}</strong> matching your search:</p>`;
			} else {
				message += `<p>I found <strong>${result.count} ${doctypeLabel}</strong> matching your search:</p>`;
			}

			// Display results in a clean, readable format
			message += '<div style="margin-top: 12px;">';
			results.forEach((item, index) => {
				// Determine name field based on doctype
				let itemName = '';
				let itemUrl = '';
				
				if (detectedDoctype === 'Customer') {
					itemName = item.customer_name || item.name;
					itemUrl = `${window.location.origin}/app/customer/${encodeURIComponent(item.name)}`;
				} else if (detectedDoctype === 'Item') {
					itemName = item.item_name || item.item_code || item.name;
					itemUrl = `${window.location.origin}/app/item/${encodeURIComponent(item.name)}`;
				} else {
					itemName = item.name || item[`${detectedDoctype.toLowerCase()}_name`] || 'Unknown';
					itemUrl = `${window.location.origin}/app/${detectedDoctype.toLowerCase().replace(/\s+/g, '-')}/${encodeURIComponent(item.name)}`;
				}
				
				message += `<div style="margin-bottom: 16px; padding-bottom: 12px; border-bottom: 1px solid #e5e7eb;">`;
				message += `<div style="font-weight: 600; font-size: 15px; color: #1f2937; margin-bottom: 6px;">${escapeHtml(itemName)}</div>`;
				
				// Build info line with available details (doctype-specific)
				const details = [];
				if (detectedDoctype === 'Customer') {
					if (item.mobile_no) details.push(`<span style="color: #4b5563;">📱 ${escapeHtml(item.mobile_no)}</span>`);
					if (item.email_id) details.push(`<span style="color: #4b5563;">📧 ${escapeHtml(item.email_id)}</span>`);
					if (item.territory) details.push(`<span style="color: #4b5563;">🌍 ${escapeHtml(item.territory)}</span>`);
					if (item.customer_group) details.push(`<span style="color: #4b5563;">👥 ${escapeHtml(item.customer_group)}</span>`);
					if (item.default_currency) details.push(`<span style="color: #4b5563;">💰 ${escapeHtml(item.default_currency)}</span>`);
				} else if (detectedDoctype === 'Item') {
					if (item.item_code) details.push(`<span style="color: #4b5563;">Code: ${escapeHtml(item.item_code)}</span>`);
					if (item.item_group) details.push(`<span style="color: #4b5563;">Group: ${escapeHtml(item.item_group)}</span>`);
					if (item.stock_uom) details.push(`<span style="color: #4b5563;">UOM: ${escapeHtml(item.stock_uom)}</span>`);
					if (item.standard_rate) details.push(`<span style="color: #4b5563;">Price: ${escapeHtml(item.standard_rate)}</span>`);
					if (item.brand) details.push(`<span style="color: #4b5563;">Brand: ${escapeHtml(item.brand)}</span>`);
				} else {
					// Generic display for other doctypes
					Object.keys(item).slice(0, 5).forEach(key => {
						if (key !== 'name' && item[key] && typeof item[key] !== 'object') {
							details.push(`<span style="color: #4b5563;">${escapeHtml(key)}: ${escapeHtml(String(item[key]))}</span>`);
						}
					});
				}
				
				if (details.length > 0) {
					message += `<div style="font-size: 13px; margin-bottom: 8px; line-height: 1.5;">${details.join(' <span style="color: #9ca3af;">•</span> ')}</div>`;
				}
				
				message += `<a href="${itemUrl}" target="_blank" style="color: #3b82f6; text-decoration: none; font-size: 13px; font-weight: 500;">View ${detectedDoctype || 'Item'} →</a>`;
				message += `</div>`;
			});
			message += '</div>';
		} else {
			message = `<p>I couldn't find any ${doctypeLabel} matching your search criteria.</p><p style="margin-top: 8px; color: #6b7280;">💡 Try adjusting your search terms or filters.</p>`;
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

	// Answer user's question based on document data using AI
	const answerQuestionFromDocument = async (document, doctype, question) => {
		try {
			showTypingIndicator();
			
			// Create a clean summary of the document for the AI
			const documentSummary = {
				doctype: doctype,
				name: document.name || document.item_code || document[`${doctype.toLowerCase()}_name`] || 'Unknown',
				// Include all relevant fields, but format nicely
				data: document
			};
			
			// Create a focused prompt for the AI
			// Format the document data more intelligently, especially for nested structures like uoms
			let formattedData = '';
			
			// Helper to extract text from HTML description
			const extractTextFromHTML = (html) => {
				if (!html) return 'N/A';
				// Remove HTML tags and decode entities
				return html.replace(/<[^>]*>/g, '').replace(/&nbsp;/g, ' ').replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').trim();
			};
			
			if (doctype === 'Item') {
				// Format Item data nicely for better AI understanding
				const itemName = document.item_name || document.item_code || document.name;
				const description = extractTextFromHTML(document.description);
				const uomsInfo = document.uoms && Array.isArray(document.uoms) && document.uoms.length > 0
					? document.uoms.map(uom => `- ${uom.uom}: conversion_factor = ${uom.conversion_factor}`).join('\n')
					: 'None';
				
				// Include stock-related quantities if available
				const stockInfo = document.stock && Array.isArray(document.stock) && document.stock.length > 0
					? document.stock.map(s => 
						`  Warehouse: ${s.warehouse || 'N/A'}, Actual Qty: ${s.actual_qty || 0}, Projected Qty: ${s.projected_qty || 0}`
					  ).join('\n')
					: 'No stock information available';
				
				formattedData = `Item Information:
- Item Name/Code: ${itemName}
- Description: ${description}
- Item Group: ${document.item_group || 'N/A'}
- Stock UOM: ${document.stock_uom || 'N/A'}
- Standard Rate: ${document.standard_rate || 0}
- Is Stock Item: ${document.is_stock_item ? 'Yes' : 'No'}
- Total Projected Quantity: ${document.total_projected_qty !== undefined ? document.total_projected_qty : 'N/A'}

Available UOMs with Conversion Factors:
${uomsInfo}

Stock Information:
${stockInfo}

Full Document Data (for complete reference):
${JSON.stringify(documentSummary, null, 2)}`;
			} else {
				formattedData = `${doctype} Document Data:
${JSON.stringify(documentSummary, null, 2)}`;
			}
			
			const prompt = `You have the complete ${doctype} document data. Answer the user's question by extracting the specific information requested from the data below. Be direct, concise, and accurate. Only provide what was asked for.

${formattedData}

User's Question: ${question}

Instructions:
- Extract the exact information requested from the document data above
- For UOMs and conversion factors, look in the "uoms" array or the formatted UOMs section above
- For descriptions, look in the "description" field (HTML tags have been removed)
- For quantities (projected qty, actual qty, etc.), look in the "total_projected_qty" field or "stock" array
- For total_projected_qty, use the value shown in "Total Projected Quantity" above
- Be specific and provide the exact values - if a value is 0, say "0", don't say it's not available
- If asking about multiple items (e.g., "all UOMs"), list them clearly
- Format your answer clearly and concisely
- IMPORTANT: If the data shows a value (even if it's 0), provide that value directly. Don't say you can't find it.`;
			
			const formData = new FormData();
			formData.append('message', prompt);
			
			const response = await fetch('/api/method/exim_backend.api.ai_chat.process_chat', {
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
			
			// The process_chat API returns: {status: "success", message: "AI response", ...}
			if (result && (result.status === 'success' || result.message)) {
				const aiAnswer = result.message || 'No answer provided';
				// Clean the answer (remove JSON code blocks if present)
				let cleanAnswer = aiAnswer.replace(/```json[\s\S]*?```/g, '').replace(/```[\s\S]*?```/g, '').trim();
				// Remove any remaining JSON structure if it's just the action
				cleanAnswer = cleanAnswer.replace(/^\s*\{[\s\S]*"action"[\s\S]*\}\s*$/g, '').trim();
				
				if (cleanAnswer && cleanAnswer.length > 0) {
					addMessage(`<p>${escapeHtml(cleanAnswer)}</p>`, 'ai', null, result.token_usage);
				} else {
					// If AI didn't provide a good answer, fallback to generic display
					console.warn('AI answer was empty or invalid, falling back to generic display');
					if (doctype === 'Item') {
						displayDocumentDetails(document, doctype);
					} else if (doctype === 'Customer') {
						displayCustomerDetails(document);
					} else {
						displayDocumentDetails(document, doctype);
					}
				}
			} else {
				// Fallback to generic display if AI fails
				console.warn('AI answer failed, falling back to generic display');
				if (doctype === 'Item') {
					displayDocumentDetails(document, doctype);
				} else if (doctype === 'Customer') {
					displayCustomerDetails(document);
				} else {
					displayDocumentDetails(document, doctype);
				}
			}
		} catch (error) {
			hideTypingIndicator();
			console.error('Error getting AI answer from document:', error);
			// Fallback to generic display on error
			if (doctype === 'Item') {
				displayDocumentDetails(document, doctype);
			} else if (doctype === 'Customer') {
				displayCustomerDetails(document);
			} else {
				displayDocumentDetails(document, doctype);
			}
		}
	};

	// Handle get customer details
	const handleGetDocumentDetails = async (action, originalQuestion = '') => {
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
				const errorText = await response.text();
				console.error('HTTP error response:', response.status, errorText);
				throw new Error(`HTTP error! status: ${response.status}, body: ${errorText}`);
			}

			const responseData = await response.json();
			console.log('Raw API responseData:', responseData);
			
			const result = responseData.message || responseData;
			
			// Debug logging - ALWAYS log this
			console.log('═══════════════════════════════════════════════════════');
			console.log('📋 GET DOCUMENT DETAILS API RESPONSE');
			console.log('═══════════════════════════════════════════════════════');
			console.log('Full responseData:', JSON.stringify(responseData, null, 2));
			console.log('Extracted result:', JSON.stringify(result, null, 2));
			console.log('Result status:', result?.status);
			console.log('Result keys:', result ? Object.keys(result) : 'result is null/undefined');
			console.log('Doctype:', doctype);
			console.log('Name:', name);
			console.log('═══════════════════════════════════════════════════════');
			
			hideTypingIndicator();

			// Validate result exists
			if (!result) {
				console.error('❌ CRITICAL: result is null/undefined!');
				addMessage(`❌ Error: No response received from server.`, 'ai');
				return;
			}

			// Handle both success and error cases
			if (result.status === 'success') {
				// Support doctype-specific and generic document formats
				// Try different possible keys based on doctype
				let document = null;
				if (doctype === 'Customer') {
					document = result.customer || result.document;
				} else if (doctype === 'Item') {
					document = result.item || result.document;
				} else {
					// Generic: try doctype-specific key first, then generic
					const doctypeKey = doctype.toLowerCase();
					document = result[doctypeKey] || result.document;
				}
				
				console.log('Extracted document:', document);
				console.log('Document type:', typeof document);
				console.log('Full result structure:', JSON.stringify(result, null, 2));
				
				// Check if document exists and is a valid object
				if (!document || typeof document !== 'object' || Array.isArray(document)) {
					console.error('Document is invalid. Full result:', result);
					const errorDetails = result.message || 'Document data is missing or invalid';
					addMessage(`❌ ${errorDetails}`, 'ai');
					return;
				}
				
				// Validate document has at least a name or identifier
				if (!document.name && !document.item_code && !document[`${doctype.toLowerCase()}_name`]) {
					console.error('Document missing identifier. Document:', document);
					addMessage(`❌ Document data is incomplete. Missing identifier.`, 'ai');
					return;
				}
				
				// Final safety check before calling display functions
				if (!document || typeof document !== 'object' || Array.isArray(document)) {
					console.error('Final validation failed - document is invalid before display:', { 
						document, 
						doctype, 
						result,
						documentType: typeof document,
						isArray: Array.isArray(document)
					});
					addMessage(`❌ Error: Invalid document data received from server. Please check console for details.`, 'ai');
					return;
				}
				
				// Additional check: ensure document has required properties
				if (doctype === 'Item' && !document.name && !document.item_code && !document.item_name) {
					console.error('Item document missing all identifiers:', document);
					addMessage(`❌ Error: Item document is missing required fields (name, item_code, item_name).`, 'ai');
					return;
				}
				
				// If original question exists, send document data to AI to answer the specific question
				if (originalQuestion && originalQuestion.trim()) {
					console.log('Original question detected, sending to AI for intelligent extraction:', originalQuestion);
					await answerQuestionFromDocument(document, doctype, originalQuestion);
				} else {
					// Call display functions with additional safety (fallback to generic display)
					try {
						if (doctype === 'Customer') {
							if (typeof displayCustomerDetails === 'function') {
								displayCustomerDetails(document);
							} else {
								throw new Error('displayCustomerDetails function not found');
							}
						} else if (doctype === 'Item') {
							// Final check before calling - document must exist and be valid
							if (!document || typeof document !== 'object') {
								throw new Error(`Document is ${document === null ? 'null' : typeof document} - cannot display`);
							}
							if (typeof displayDocumentDetails === 'function') {
								displayDocumentDetails(document, doctype);
							} else {
								throw new Error('displayDocumentDetails function not found');
							}
						} else {
							if (typeof displayDocumentDetails === 'function') {
								displayDocumentDetails(document, doctype);
							} else {
								throw new Error('displayDocumentDetails function not found');
							}
						}
					} catch (displayError) {
						console.error('Error calling display function:', displayError, { document, doctype });
						addMessage(`❌ Error displaying document: ${displayError.message || 'Unknown error'}`, 'ai');
					}
				}
			} else {
				// Handle error response
				const errorMsg = result.message || 'Unknown error occurred';
				console.error('API returned error status:', result);
				addMessage(`❌ ${errorMsg}`, 'ai');
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
		try {
			// Validate document exists and is a valid object
			if (!document || typeof document !== 'object' || Array.isArray(document)) {
				console.error('displayDocumentDetails: document is invalid', { document, doctype });
				addMessage(`❌ Error: Document data is missing or invalid.`, 'ai');
				return;
			}
			
			// Validate doctype
			if (!doctype || typeof doctype !== 'string') {
				console.error('displayDocumentDetails: doctype is invalid', { document, doctype });
				addMessage(`❌ Error: Invalid document type.`, 'ai');
				return;
			}
			
			// Get document name/ID - handle different doctype naming conventions
			// Use optional chaining and nullish coalescing for safety
			const docName = document?.name || document?.item_code || document?.[`${doctype.toLowerCase()}_name`] || 'Unknown';
			const docUrl = `${window.location.origin}/app/${doctype.toLowerCase().replace(/\s+/g, '-')}/${encodeURIComponent(docName)}`;
			const nameField = document?.item_name || document?.name || document?.[`${doctype.toLowerCase()}_name`] || docName;
			
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
		} catch (error) {
			console.error('displayDocumentDetails error:', error, { document, doctype });
			addMessage(`❌ Error displaying document details: ${error.message || 'Unknown error'}`, 'ai');
		}
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

