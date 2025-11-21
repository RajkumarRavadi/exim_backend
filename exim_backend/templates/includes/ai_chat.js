// AI Chat Interface JavaScript - Custom Modern UI
(function () {
	'use strict';

	// DOM Elements
	const messagesContainer = document.getElementById('messagesContainer');
	const messagesWrapper = document.getElementById('messagesWrapper');
	const messageInput = document.getElementById('messageInput');
	const sendBtn = document.getElementById('sendBtn');
	const attachBtn = document.getElementById('attachBtn');
	const fileInput = document.getElementById('fileInput');
	const filePreview = document.getElementById('filePreview');
	const removeFileBtn = document.getElementById('removeFileBtn');
	const clearHistoryBtn = document.getElementById('clearHistoryBtn');
	const newChatBtn = document.getElementById('newChatBtn');
	const emptyState = document.getElementById('emptyState');

	// State
	let currentImage = null;
	let currentFile = null; // For PDFs
	let currentFileType = null; // 'image' or 'pdf'
	let isProcessing = false;
	let sessionId = localStorage.getItem('ai_chat_session_id') || generateSessionId();

	// Toggle for intelligent query system (set to true to use new system)
	// INTELLIGENT QUERY SYSTEM DISABLED - Using traditional functional approach
	let useIntelligentQuery = false; // DISABLED - Commented out intelligent query features

	// Log initial state
	// console.log('%c🧠 Intelligent Query System Status:', 'color: #2196F3; font-weight: bold;', useIntelligentQuery ? 'ENABLED' : 'DISABLED');

	// Generate or retrieve session ID
	function generateSessionId() {
		const id = 'chat_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
		localStorage.setItem('ai_chat_session_id', id);
		return id;
	}

	// Initialize
	const init = () => {
		setupEventListeners();
		console.log('AI Chat initialized with session:', sessionId);
	};

	// Event Listeners
	const setupEventListeners = () => {
		if (!sendBtn || !messageInput) {
			console.error('Required DOM elements not found!');
			return;
		}

		sendBtn.addEventListener('click', handleSendMessage);
		if (attachBtn) attachBtn.addEventListener('click', () => fileInput.click());
		if (fileInput) fileInput.addEventListener('change', handleFileUpload);
		if (removeFileBtn) removeFileBtn.addEventListener('click', handleRemoveFile);
		if (clearHistoryBtn) clearHistoryBtn.addEventListener('click', handleClearHistory);
		if (newChatBtn) newChatBtn.addEventListener('click', handleNewChat);

		// Example prompts
		const examplePrompts = document.querySelectorAll('.example-prompt');
		examplePrompts.forEach(prompt => {
			prompt.addEventListener('click', () => {
				messageInput.value = prompt.dataset.prompt;
				messageInput.focus();
			});
		});

		// Enter to send
		messageInput.addEventListener('keydown', (e) => {
			if (e.key === 'Enter' && !e.shiftKey) {
				e.preventDefault();
				handleSendMessage();
			}
		});

		// Auto-resize textarea
		messageInput.addEventListener('input', () => {
			messageInput.style.height = 'auto';
			messageInput.style.height = Math.min(messageInput.scrollHeight, 200) + 'px';
		});
	};

	// Handle file upload (image or PDF)
	const handleFileUpload = (e) => {
		const file = e.target.files[0];
		if (!file) return;

		const isPDF = file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf');
		const isImage = file.type.startsWith('image/');

		if (!isPDF && !isImage) {
			showNotification('Please upload a valid image or PDF file', 'error');
			return;
		}

		if (isPDF) {
			currentFile = file;
			currentFileType = 'pdf';
			currentImage = null;
			showFilePreview('📄', file.name, formatFileSize(file.size));
		} else {
			currentImage = file;
			currentFileType = 'image';
			currentFile = null;
			const reader = new FileReader();
			reader.onload = (event) => {
				showFilePreview('🖼️', file.name, formatFileSize(file.size), event.target.result);
			};
			reader.readAsDataURL(file);
		}
	};

	// Show file preview
	const showFilePreview = (icon, name, size, imageUrl = null) => {
		const fileIcon = document.getElementById('fileIcon');
		const fileName = document.getElementById('fileName');
		const fileSize = document.getElementById('fileSize');

		if (!fileIcon || !fileName || !fileSize) return;

		if (imageUrl) {
			fileIcon.style.backgroundImage = `url(${imageUrl})`;
			fileIcon.style.backgroundSize = 'cover';
			fileIcon.style.backgroundPosition = 'center';
			fileIcon.textContent = '';
		} else {
			fileIcon.style.backgroundImage = 'none';
			fileIcon.textContent = icon;
		}

		fileName.textContent = name;
		fileSize.textContent = size;
		filePreview.classList.add('active');
	};

	// Handle remove file
	const handleRemoveFile = () => {
		if (!filePreview) return;
		filePreview.classList.remove('active');
		currentImage = null;
		currentFile = null;
		currentFileType = null;
		if (fileInput) fileInput.value = '';
	};

	// Format file size
	const formatFileSize = (bytes) => {
		if (bytes === 0) return '0 Bytes';
		const k = 1024;
		const sizes = ['Bytes', 'KB', 'MB', 'GB'];
		const i = Math.floor(Math.log(bytes) / Math.log(k));
		return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
	};

	// Handle new chat
	const handleNewChat = () => {
		sessionId = generateSessionId();
		if (messagesWrapper) messagesWrapper.innerHTML = '';
		if (emptyState) emptyState.style.display = 'flex';
		handleRemoveFile();
		if (messageInput) messageInput.value = '';
		showNotification('New chat started', 'success');
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
				if (messagesWrapper) messagesWrapper.innerHTML = '';
				if (emptyState) emptyState.style.display = 'flex';
				showNotification('Conversation history cleared', 'success');
			} else {
				showNotification('Failed to clear history', 'error');
			}
		} catch (error) {
			console.error('Clear history error:', error);
			showNotification('Failed to clear history. Please try again.', 'error');
		}
	};

	// Handle send message
	const handleSendMessage = async () => {
		const message = messageInput.value.trim();

		// Validate input
		if (!message && !currentImage && !currentFile) {
			showNotification('Please enter a message or attach a file', 'error');
			return;
		}

		if (isProcessing) return;

		// Hide empty state
		if (emptyState) {
			emptyState.style.display = 'none';
		}

		// Add user message
		if (message) {
			addMessage('user', message);
		}

		if (currentImage) {
			const reader = new FileReader();
			reader.onload = (e) => {
				addImageMessage('user', e.target.result);
			};
			reader.readAsDataURL(currentImage);
		}

		if (currentFile) {
			const pdfMessage = message ?
				`${message}\n\n📄 Analyzing: ${currentFile.name}` :
				`📄 Analyzing PDF for sales order: ${currentFile.name}`;
			if (!message) {
				addMessage('user', pdfMessage);
			}
		}

		// Store message details
		const messageToSend = message;
		const imageToSend = currentImage;
		const fileToSend = currentFile;
		const fileTypeToSend = currentFileType;

		// Clear input
		messageInput.value = '';
		messageInput.style.height = 'auto';
		handleRemoveFile();

		// Show typing indicator
		const typingId = showTypingIndicator();

		// Disable send button
		isProcessing = true;
		sendBtn.disabled = true;

		// Send to API - Choose between old and new system
		try {
			let response;

			// INTELLIGENT QUERY SYSTEM DISABLED - Always use traditional functional approach
			// Check if we should use intelligent query (only for text queries, not file uploads)
			// if (useIntelligentQuery && messageToSend && !imageToSend && !fileToSend) {
			// 	console.log('%c🧠 Using Intelligent Query System', 'color: #2196F3; font-weight: bold; font-size: 14px;');
			// 	console.log('Query:', messageToSend);
			// 	console.log('useIntelligentQuery flag:', useIntelligentQuery);
			// 	try {
			// 		response = await sendIntelligentQuery(messageToSend);
			// 		console.log('Intelligent Query Response:', response);
			// 	} catch (error) {
			// 		console.error('Intelligent Query failed, error will be shown to user:', error);
			// 		// Re-throw to show error in UI instead of silently falling back
			// 		throw error;
			// 	}
			// } else {
			// 	const reason = !useIntelligentQuery ? 'useIntelligentQuery is false' : 
			// 	               !messageToSend ? 'no message' : 
			// 	               'file/image attached';
			// 	console.log('%c⚡ Using Traditional System', 'color: #4CAF50; font-weight: bold; font-size: 14px;');
			// 	console.log('Reason:', reason);
			// 	response = await sendChatMessage(messageToSend, imageToSend, fileToSend, fileTypeToSend);
			// }

			// Always use traditional functional approach
			console.log('%c⚡ Using Traditional Functional System', 'color: #4CAF50; font-weight: bold; font-size: 14px;');
			response = await sendChatMessage(messageToSend, imageToSend, fileToSend, fileTypeToSend);

			hideTypingIndicator(typingId);

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

			// INTELLIGENT QUERY SYSTEM DISABLED
			// Handle Intelligent Query Response
			// if (response.execution_type) {
			// 	console.log('%c🧠 Intelligent Query Response', 'color: #2196F3; font-weight: bold;');
			// 	console.log('Execution Type:', response.execution_type);
			// 	console.log('AI Reasoning:', response.ai_reasoning);
			// 	console.log('Detected DocTypes:', response.detected_doctypes);
			// 	displayIntelligentQueryResults(response);
			// 	isProcessing = false;
			// 	sendBtn.disabled = false;
			// 	return;
			// }

			console.log('Suggested action:', response.suggested_action);
			console.log('Suggested action type:', typeof response.suggested_action);

			if (response.suggested_action) {
				console.log('Action details:', JSON.stringify(response.suggested_action, null, 2));
			}

			// Handle PDF sales order response (requires_action = true)
			if (response.status === 'success' && response.requires_action && response.response) {
				console.log('PDF Sales Order Response detected');
				console.log('PDF Response data:', response.data);
				console.log('PDF Session ID:', response.session_id);

				let formattedMessage = formatPDFResponse(response.response);
				console.log('Formatted PDF message:', formattedMessage);

				// Also format and display the structured data if available
				if (response.data && typeof response.data === 'object') {
					const dataDisplay = formatPDFData(response.data);
					formattedMessage += dataDisplay;
				}

				// Add action buttons for PDF confirmation
				const actionButtons = createPDFActionButtons(response.session_id, response.data);
				console.log('Action buttons:', actionButtons);
				const messageWithActions = formattedMessage + actionButtons;
				console.log('Complete message with actions:', messageWithActions);

				addMessage('ai', messageWithActions, null, null);
				isProcessing = false;
				sendBtn.disabled = false;
				return;
			}

			if (response.status === 'success') {
				// Remove JSON from AI message if suggested action exists
				let cleanMessage = response.message || response.response || '';

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
						// Strip any HTML tags that AI might have returned (shouldn't happen, but just in case)
						let messageText = cleanMessage;
						if (/<[a-z][\s\S]*>/i.test(cleanMessage)) {
							// Contains HTML tags - strip them and use the text content
							messageText = stripHtmlTags(cleanMessage);
						}

						// Convert markdown to HTML before passing to addMessage
						const hasMarkdown = /[\*\-\+]\s+|\*\*|__|`|```/.test(messageText);
						if (hasMarkdown) {
							addMessage('ai', markdownToHtml(messageText), response.token_usage, null);
						} else {
							// Plain text - wrap in paragraph
							addMessage('ai', `<p class="ai-paragraph">${escapeHtml(messageText)}</p>`, response.token_usage, null);
						}
					}
					// Pass the original user message for context
					autoExecuteAction(response.suggested_action, message);
				} else {
					// Strip any HTML tags that AI might have returned (shouldn't happen, but just in case)
					let messageText = cleanMessage;
					if (/<[a-z][\s\S]*>/i.test(cleanMessage)) {
						// Contains HTML tags - strip them and use the text content
						messageText = stripHtmlTags(cleanMessage);
					}

					// Convert markdown to HTML before passing to addMessage
					const hasMarkdown = /[\*\-\+]\s+|\*\*|__|`|```/.test(messageText);
					if (hasMarkdown) {
						addMessage('ai', markdownToHtml(messageText), response.token_usage, response.suggested_action);
					} else {
						// Plain text - wrap in paragraph
						addMessage('ai', `<p class="ai-paragraph">${escapeHtml(messageText)}</p>`, response.token_usage, response.suggested_action);
					}
				}
			} else {
				showNotification(response.message || 'An error occurred', 'error');
			}
		} catch (error) {
			hideTypingIndicator(typingId);
			showNotification('Failed to send message. Please try again.', 'error');
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
	const sendChatMessage = async (message, image, file, fileType) => {
		const formData = new FormData();
		formData.append('message', message);
		formData.append('session_id', sessionId);

		if (image) {
			formData.append('image', image);
		}

		if (file && fileType === 'pdf') {
			// Send PDF file
			formData.append('pdf', file);
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

	// Strip HTML tags from text (in case AI returns HTML as text)
	const stripHtmlTags = (text) => {
		if (!text) return '';
		const div = document.createElement('div');
		div.innerHTML = text;
		return div.textContent || div.innerText || '';
	};

	// Format PDF Sales Order response with nice HTML
	const formatPDFResponse = (text) => {
		if (!text) return '';

		let html = '<div style="font-family: system-ui, -apple-system, sans-serif; line-height: 1.6;">';

		// Split into lines
		const lines = text.split('\n').filter(line => line.trim());

		for (let i = 0; i < lines.length; i++) {
			const line = lines[i].trim();

			// Success header
			if (line.includes('✅') || line.includes('PDF Analyzed Successfully')) {
				html += `<div style="background: #ecfdf5; border-left: 4px solid #10b981; padding: 12px 16px; margin-bottom: 16px; border-radius: 6px;">
					<strong style="color: #059669; font-size: 16px;">${escapeHtml(line)}</strong>
				</div>`;
				continue;
			}

			// Section headers with emojis
			if (line.match(/^\*\*(.+?)\*\*:/) || line.match(/^(.+?):/)) {
				const match = line.match(/^\*\*(.+?)\*\*:\s*(.*)/) || line.match(/^(.+?):\s*(.*)/);
				if (match) {
					const label = match[1].replace(/\*\*/g, '');
					const value = match[2].replace(/\*\*/g, '');
					html += `<div style="margin: 8px 0; display: flex; gap: 8px;">
						<span style="color: #6366f1; font-weight: 600; min-width: 140px;">${escapeHtml(label)}:</span>
						<span style="color: #1f2937; font-weight: 500;">${escapeHtml(value)}</span>
					</div>`;
					continue;
				}
			}

			// Items section header
			if (line.includes('📦 Items:')) {
				html += `<div style="margin-top: 16px; margin-bottom: 8px; padding: 8px 0; border-top: 1px solid #e5e7eb;">
					<strong style="color: #4f46e5; font-size: 15px;">${escapeHtml(line)}</strong>
				</div>`;
				continue;
			}

			// Item details (numbered lines)
			if (line.match(/^\d+\.\s+\*\*(.+?)\*\*/)) {
				const match = line.match(/^(\d+)\.\s+\*\*(.+?)\*\*/);
				if (match) {
					const itemNum = match[1];
					const itemName = match[2];
					html += `<div style="margin: 12px 0 4px 20px; background: #f9fafb; padding: 10px 12px; border-radius: 6px; border-left: 3px solid #818cf8;">
						<strong style="color: #4338ca; font-size: 14px;">${escapeHtml(itemNum)}. ${escapeHtml(itemName)}</strong>`;
					continue;
				}
			}

			// Item sub-details (• Qty, • Rate)
			if (line.match(/^\s*•\s+(.+?):/)) {
				const match = line.match(/^\s*•\s+(.+?):\s*(.+)/);
				if (match) {
					const prop = match[1];
					const val = match[2];
					html += `<div style="margin-left: 12px; color: #6b7280; font-size: 13px;">• ${escapeHtml(prop)}: <span style="color: #111827; font-weight: 500;">${escapeHtml(val)}</span></div>`;
					continue;
				}
			}

			// Close item div if next line is not a sub-detail
			if (html.includes('border-left: 3px solid #818cf8') && !line.match(/^\s*•/) && !line.match(/^\d+\./)) {
				html += '</div>';
			}

			// Action prompts section
			if (line.includes('What would you like to do')) {
				html += `<div style="margin-top: 20px; background: #fef3c7; border-left: 4px solid #f59e0b; padding: 12px 16px; border-radius: 6px;">
					<strong style="color: #b45309; font-size: 14px;">${escapeHtml(line)}</strong>`;
				continue;
			}

			// Action bullet points
			if (line.match(/^•\s+Type\s+\*\*/)) {
				const actionText = line.replace(/\*\*/g, '').replace(/^•\s*/, '');
				html += `<div style="margin: 6px 0 6px 12px; color: #78350f; font-size: 13px;">• ${escapeHtml(actionText)}</div>`;
				continue;
			}

			// Example lines
			if (line.includes('Example:')) {
				html += `<div style="margin-left: 28px; color: #9ca3af; font-size: 12px; font-style: italic;">${escapeHtml(line)}</div>`;
				continue;
			}

			// Default paragraph
			if (line && !line.match(/^\s*$/)) {
				html += `<p style="margin: 8px 0; color: #374151;">${escapeHtml(line)}</p>`;
			}
		}

		// Close action prompts div if it was opened
		if (html.includes('background: #fef3c7')) {
			html += '</div>';
		}

		// Close the main container div
		html += '</div>';

		return html;
	};

	// Format structured PDF data for display
	const formatPDFData = (data) => {
		if (!data || typeof data !== 'object') return '';

		let html = '<div style="margin-top: 20px; padding: 20px; background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); border-radius: 12px; border: 1px solid #dee2e6;">';
		html += '<h3 style="font-size: 18px; font-weight: 700; color: #1f2937; margin: 0 0 16px 0; padding-bottom: 12px; border-bottom: 2px solid #667eea;">📋 Extracted Sales Order Data</h3>';

		// Display main fields
		const mainFields = ['customer', 'transaction_date', 'delivery_date', 'po_no', 'company'];
		mainFields.forEach(field => {
			if (data[field] !== null && data[field] !== undefined && data[field] !== '') {
				const label = field.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
				html += `<div style="margin: 8px 0; padding: 8px; background: white; border-radius: 6px;">
					<span style="color: #6366f1; font-weight: 600; min-width: 160px; display: inline-block;">${escapeHtml(label)}:</span>
					<span style="color: #1f2937; font-weight: 500;">${escapeHtml(String(data[field]))}</span>
				</div>`;
			}
		});

		// Display items
		if (data.items && Array.isArray(data.items) && data.items.length > 0) {
			html += '<div style="margin-top: 16px; padding-top: 16px; border-top: 2px solid #e5e7eb;">';
			html += '<h4 style="font-size: 16px; font-weight: 600; color: #4f46e5; margin-bottom: 12px;">📦 Items (' + data.items.length + ')</h4>';

			data.items.forEach((item, index) => {
				html += `<div style="margin: 12px 0; padding: 12px; background: white; border-radius: 8px; border-left: 4px solid #818cf8;">`;
				html += `<div style="font-weight: 700; color: #4338ca; margin-bottom: 8px;">${index + 1}. ${escapeHtml(item.item_name || item.item_code || 'Item ' + (index + 1))}</div>`;

				if (item.item_code) {
					html += `<div style="margin: 4px 0; color: #6b7280; font-size: 14px;">• Item Code: <span style="color: #1f2937; font-weight: 500;">${escapeHtml(item.item_code)}</span></div>`;
				}
				if (item.qty) {
					html += `<div style="margin: 4px 0; color: #6b7280; font-size: 14px;">• Quantity: <span style="color: #1f2937; font-weight: 500;">${escapeHtml(String(item.qty))}</span></div>`;
				}
				if (item.rate) {
					html += `<div style="margin: 4px 0; color: #6b7280; font-size: 14px;">• Rate: <span style="color: #1f2937; font-weight: 500;">${escapeHtml(String(item.rate))}</span></div>`;
				}
				if (item.amount) {
					html += `<div style="margin: 4px 0; color: #6b7280; font-size: 14px;">• Amount: <span style="color: #1f2937; font-weight: 500;">${escapeHtml(String(item.amount))}</span></div>`;
				}

				html += '</div>';
			});

			html += '</div>';
		}

		// Display warnings if any
		if (data._warnings && Array.isArray(data._warnings) && data._warnings.length > 0) {
			html += '<div style="margin-top: 16px; padding: 12px; background: #fef3c7; border-left: 4px solid #f59e0b; border-radius: 6px;">';
			html += '<strong style="color: #b45309; font-size: 14px;">⚠️ Warnings:</strong>';
			data._warnings.forEach(warning => {
				html += `<div style="margin: 4px 0; color: #78350f; font-size: 13px;">• ${escapeHtml(warning)}</div>`;
			});
			html += '</div>';
		}

		html += '</div>';
		return html;
	};

	// Create action buttons for PDF sales order confirmation
	const createPDFActionButtons = (sessionId, pdfData) => {
		if (!sessionId) return '';

		const buttonContainer = `
			<div style="
				margin-top: 24px;
				padding: 20px;
				background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
				border-radius: 12px;
				border: 2px solid #0ea5e9;
				display: flex;
				gap: 12px;
				flex-wrap: wrap;
				align-items: center;
				justify-content: center;
			">
				<button 
					onclick="handlePDFConfirm('${sessionId}')"
					style="
						background: linear-gradient(135deg, #10b981 0%, #059669 100%);
						color: white;
						border: none;
						padding: 12px 24px;
						border-radius: 8px;
						font-size: 15px;
						font-weight: 600;
						cursor: pointer;
						box-shadow: 0 4px 6px rgba(16, 185, 129, 0.3);
						transition: all 0.2s;
						display: inline-flex;
						align-items: center;
						gap: 8px;
					"
					onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 6px 12px rgba(16, 185, 129, 0.4)';"
					onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 6px rgba(16, 185, 129, 0.3)';"
				>
					✅ Confirm & Create Sales Order
				</button>
				
				<button 
					onclick="handlePDFCancel('${sessionId}')"
					style="
						background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
						color: white;
						border: none;
						padding: 12px 24px;
						border-radius: 8px;
						font-size: 15px;
						font-weight: 600;
						cursor: pointer;
						box-shadow: 0 4px 6px rgba(239, 68, 68, 0.3);
						transition: all 0.2s;
						display: inline-flex;
						align-items: center;
						gap: 8px;
					"
					onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 6px 12px rgba(239, 68, 68, 0.4)';"
					onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 6px rgba(239, 68, 68, 0.3)';"
				>
					❌ Cancel
				</button>
				
				<button 
					onclick="handlePDFShowData('${sessionId}')"
					style="
						background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
						color: white;
						border: none;
						padding: 12px 24px;
						border-radius: 8px;
						font-size: 15px;
						font-weight: 600;
						cursor: pointer;
						box-shadow: 0 4px 6px rgba(99, 102, 241, 0.3);
						transition: all 0.2s;
						display: inline-flex;
						align-items: center;
						gap: 8px;
					"
					onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 6px 12px rgba(99, 102, 241, 0.4)';"
					onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 6px rgba(99, 102, 241, 0.3)';"
				>
					👁️ Show Data
				</button>
			</div>
		`;

		return buttonContainer;
	};

	// Handle PDF confirmation
	window.handlePDFConfirm = async (sessionId) => {
		if (!sessionId) {
			showNotification('Session ID not found', 'error');
			return;
		}

		const typingId = showTypingIndicator();
		isProcessing = true;
		sendBtn.disabled = true;

		try {
			const response = await fetch('/api/method/exim_backend.api.pdf_chat_integration.handle_pdf_response', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					'X-Frappe-CSRF-Token': getCSRFToken()
				},
				body: JSON.stringify({
					conversation_id: sessionId,
					user_message: 'confirm'
				})
			});

			if (!response.ok) {
				throw new Error(`HTTP error! status: ${response.status}`);
			}

			const result = await response.json();
			const pdfResponse = result.message || result;

			console.log('PDF Confirm Response:', pdfResponse);
			console.log('Response status:', pdfResponse.status);
			console.log('Response message:', pdfResponse.message);
			console.log('Response response:', pdfResponse.response);

			hideTypingIndicator(typingId);
			isProcessing = false;
			sendBtn.disabled = false;

			// Add user confirmation message
			addMessage('user', '✅ Confirm & Create Sales Order');

			// Check for success
			if (pdfResponse.status === 'success' || pdfResponse.message?.includes('success') || pdfResponse.response?.includes('success')) {
				// Get the success message
				const successMessage = pdfResponse.message || pdfResponse.response || pdfResponse.sales_order_name || 'Sales order created successfully!';

				// Create a nice success message display
				let successHtml = '<div style="font-family: system-ui, -apple-system, sans-serif; line-height: 1.6;">';
				successHtml += '<div style="background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%); border-left: 4px solid #10b981; padding: 16px 20px; margin-bottom: 16px; border-radius: 8px; box-shadow: 0 2px 8px rgba(16, 185, 129, 0.2);">';
				successHtml += '<div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">';
				successHtml += '<span style="font-size: 24px;">✅</span>';
				successHtml += '<strong style="color: #059669; font-size: 18px;">Sales Order Created Successfully!</strong>';
				successHtml += '</div>';

				// Add sales order details if available
				if (pdfResponse.sales_order_name) {
					successHtml += `<div style="margin-top: 12px; padding-top: 12px; border-top: 1px solid #a7f3d0;">`;
					successHtml += `<div style="color: #047857; font-size: 14px; margin: 4px 0;"><strong>Sales Order:</strong> ${escapeHtml(pdfResponse.sales_order_name)}</div>`;
					if (pdfResponse.customer) {
						successHtml += `<div style="color: #047857; font-size: 14px; margin: 4px 0;"><strong>Customer:</strong> ${escapeHtml(pdfResponse.customer)}</div>`;
					}
					if (pdfResponse.grand_total) {
						successHtml += `<div style="color: #047857; font-size: 14px; margin: 4px 0;"><strong>Grand Total:</strong> ${escapeHtml(String(pdfResponse.grand_total))}</div>`;
					}
					successHtml += `</div>`;
				}

				// Add the message text if it's different from the default
				if (successMessage && !successMessage.includes('Sales order created successfully')) {
					successHtml += `<div style="margin-top: 12px; padding-top: 12px; border-top: 1px solid #a7f3d0; color: #047857; font-size: 14px;">${escapeHtml(successMessage)}</div>`;
				}

				successHtml += '</div>';
				successHtml += '</div>';

				addMessage('ai', successHtml, null, null);
				showNotification('Sales order created successfully!', 'success');
			} else {
				// Error case
				const errorMessage = pdfResponse.message || pdfResponse.response || 'Failed to create sales order';
				const errorHtml = `<div style="background: #fef2f2; border-left: 4px solid #ef4444; padding: 16px 20px; border-radius: 8px;">
					<strong style="color: #dc2626; font-size: 16px;">❌ Error</strong>
					<div style="color: #991b1b; font-size: 14px; margin-top: 8px;">${escapeHtml(errorMessage)}</div>
				</div>`;
				addMessage('ai', errorHtml, null, null);
				showNotification(errorMessage, 'error');
			}
		} catch (error) {
			hideTypingIndicator(typingId);
			isProcessing = false;
			sendBtn.disabled = false;
			console.error('Error confirming PDF:', error);
			showNotification('Failed to confirm PDF: ' + error.message, 'error');
		}
	};

	// Handle PDF cancellation
	window.handlePDFCancel = async (sessionId) => {
		if (!sessionId) {
			showNotification('Session ID not found', 'error');
			return;
		}

		const typingId = showTypingIndicator();
		isProcessing = true;
		sendBtn.disabled = true;

		try {
			const response = await fetch('/api/method/exim_backend.api.pdf_chat_integration.handle_pdf_response', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					'X-Frappe-CSRF-Token': getCSRFToken()
				},
				body: JSON.stringify({
					conversation_id: sessionId,
					user_message: 'cancel'
				})
			});

			if (!response.ok) {
				throw new Error(`HTTP error! status: ${response.status}`);
			}

			const result = await response.json();
			const pdfResponse = result.message || result;

			hideTypingIndicator(typingId);
			isProcessing = false;
			sendBtn.disabled = false;

			addMessage('user', '❌ Cancel');
			const formattedMessage = formatPDFResponse(pdfResponse.message || pdfResponse.response || 'PDF session cancelled.');
			addMessage(formattedMessage, 'ai', null, null);
			showNotification('PDF session cancelled', 'info');
		} catch (error) {
			hideTypingIndicator(typingId);
			isProcessing = false;
			sendBtn.disabled = false;
			console.error('Error cancelling PDF:', error);
			showNotification('Failed to cancel PDF: ' + error.message, 'error');
		}
	};

	// Handle PDF show data
	window.handlePDFShowData = async (sessionId) => {
		if (!sessionId) {
			showNotification('Session ID not found', 'error');
			return;
		}

		const typingId = showTypingIndicator();
		isProcessing = true;
		sendBtn.disabled = true;

		try {
			const response = await fetch('/api/method/exim_backend.api.pdf_chat_integration.handle_pdf_response', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					'X-Frappe-CSRF-Token': getCSRFToken()
				},
				body: JSON.stringify({
					conversation_id: sessionId,
					user_message: 'show data'
				})
			});

			if (!response.ok) {
				throw new Error(`HTTP error! status: ${response.status}`);
			}

			const result = await response.json();
			const pdfResponse = result.message || result;

			hideTypingIndicator(typingId);
			isProcessing = false;
			sendBtn.disabled = false;

			addMessage('user', '👁️ Show Data');
			const formattedMessage = formatPDFResponse(pdfResponse.message || pdfResponse.response || 'No data available.');
			addMessage(formattedMessage, 'ai', null, null);
		} catch (error) {
			hideTypingIndicator(typingId);
			isProcessing = false;
			sendBtn.disabled = false;
			console.error('Error showing PDF data:', error);
			showNotification('Failed to show PDF data: ' + error.message, 'error');
		}
	};

	// Convert markdown to HTML with clean, minimal styling
	const markdownToHtml = (text) => {
		if (!text) return '';

		// First, escape HTML to prevent XSS
		let html = escapeHtml(text);

		// Convert code blocks first (before other processing)
		html = html.replace(/```([\s\S]*?)```/g, '<pre class="ai-code-block"><code>$1</code></pre>');

		// IMPORTANT: Handle "* `field`" pattern BEFORE converting backticks to code
		// This is the most common AI format for field lists
		// Match lines that start with "* " followed by backticked text
		html = html.replace(/^\*\s+`([^`\n]+)`/gm, '<li><code class="ai-inline-code">$1</code></li>');

		// Also handle "* `field` (description)" pattern
		html = html.replace(/^\*\s+`([^`\n]+)`\s*\(([^)]+)\)/gm, '<li><code class="ai-inline-code">$1</code> ($2)</li>');

		// Now convert remaining inline code (but not inside code blocks or already converted list items)
		html = html.replace(/`([^`\n]+)`/g, '<code class="ai-inline-code">$1</code>');

		// Detect patterns like "such as `field1` `field2` `field3`" and convert to list
		// This pattern helps format field lists better (for cases without asterisks)
		html = html.replace(/(such as|including|like|for example|I need|At minimum|At a minimum)[\s:]*((?:`[^`]+`[\s,]*)+)/gi, (match, prefix, fields) => {
			// Extract individual field names
			const fieldMatches = fields.match(/`([^`]+)`/g) || [];
			if (fieldMatches.length > 1) {
				// Convert to list format
				const fieldList = fieldMatches.map(f => {
					const fieldName = f.replace(/`/g, '');
					return `<li><code class="ai-inline-code">${fieldName}</code></li>`;
				}).join('');
				return `${prefix}:<ul class="ai-field-list">${fieldList}</ul>`;
			}
			return match;
		});

		// Convert bold (**text** or __text__) - but not single asterisks used for lists
		html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
		html = html.replace(/__(.+?)__/g, '<strong>$1</strong>');

		// Convert italic (*text* or _text_) - but be careful not to match list markers
		// Only match single asterisks/underscores that are not part of bold or list markers
		html = html.replace(/(?:\s|^)\*([^*\n\s]+?)\*(?:\s|$)/g, ' <em>$1</em> ');
		html = html.replace(/(?:\s|^)_([^_\n\s]+?)_(?:\s|$)/g, ' <em>$1</em> ');

		// Split into lines for processing
		const lines = html.split('\n');
		const processedLines = [];
		let inList = false;
		let listItems = [];
		let inParagraph = false;
		let paragraphLines = [];

		for (let i = 0; i < lines.length; i++) {
			const line = lines[i];
			const trimmedLine = line.trim();

			// Check for bullet list items (*, -, +)
			// Also handle cases like "* `field`" which might already be converted to <li>
			if (/^[\*\-\+]\s+/.test(trimmedLine) || trimmedLine.startsWith('<li>')) {
				// Close paragraph if open
				if (inParagraph && paragraphLines.length > 0) {
					processedLines.push(`<p class="ai-paragraph">${paragraphLines.join(' ')}</p>`);
					paragraphLines = [];
					inParagraph = false;
				}

				if (!inList) {
					inList = true;
					listItems = [];
				}

				// If already converted to <li>, use it directly
				if (trimmedLine.startsWith('<li>')) {
					listItems.push(trimmedLine);
				} else {
					const itemText = trimmedLine.replace(/^[\*\-\+]\s+/, '');
					listItems.push(`<li>${itemText}</li>`);
				}
			}
			// Check for numbered list items (1., 2., etc.)
			else if (/^\d+\.\s+/.test(trimmedLine)) {
				// Close paragraph if open
				if (inParagraph && paragraphLines.length > 0) {
					processedLines.push(`<p class="ai-paragraph">${paragraphLines.join(' ')}</p>`);
					paragraphLines = [];
					inParagraph = false;
				}

				if (!inList) {
					inList = true;
					listItems = [];
				}
				const itemText = trimmedLine.replace(/^\d+\.\s+/, '');
				listItems.push(`<li>${itemText}</li>`);
			}
			else {
				// End current list if any
				if (inList && listItems.length > 0) {
					processedLines.push(`<ul class="ai-list">${listItems.join('')}</ul>`);
					listItems = [];
					inList = false;
				}

				// Handle regular lines - group into paragraphs
				if (trimmedLine) {
					if (!inParagraph) {
						inParagraph = true;
						paragraphLines = [];
					}
					paragraphLines.push(trimmedLine);
				} else {
					// Empty line - close paragraph if open
					if (inParagraph && paragraphLines.length > 0) {
						processedLines.push(`<p class="ai-paragraph">${paragraphLines.join(' ')}</p>`);
						paragraphLines = [];
						inParagraph = false;
					}
				}
			}
		}

		// Close any remaining list
		if (inList && listItems.length > 0) {
			processedLines.push(`<ul class="ai-list">${listItems.join('')}</ul>`);
		}

		// Close any remaining paragraph
		if (inParagraph && paragraphLines.length > 0) {
			processedLines.push(`<p class="ai-paragraph">${paragraphLines.join(' ')}</p>`);
		}

		html = processedLines.join('');

		// Clean up multiple consecutive <br> tags
		html = html.replace(/(<br>\s*){2,}/g, '<br>');

		return html;
	};

	// Add message to chat
	// Add message to chat
	const addMessage = (type, content, tokenUsage = null, suggestedAction = null) => {
		if (!messagesWrapper) return;

		const messageDiv = document.createElement('div');
		messageDiv.className = `message ${type}`;

		const avatar = document.createElement('div');
		avatar.className = 'message-avatar';
		avatar.textContent = type === 'user' ? 'U' : 'AI';

		const contentDiv = document.createElement('div');
		contentDiv.className = 'message-content';
		contentDiv.innerHTML = content;

		if (type === 'ai' && tokenUsage) {
			const tokenInfo = document.createElement('div');
			tokenInfo.className = 'token-usage';
			tokenInfo.textContent = `Tokens: ${tokenUsage.input_tokens} in + ${tokenUsage.output_tokens} out = ${tokenUsage.total_tokens} total`;
			contentDiv.appendChild(tokenInfo);
		}

		messageDiv.appendChild(avatar);
		messageDiv.appendChild(contentDiv);

		// Add suggested actions if present
		if (suggestedAction && type === 'ai') {
			const actionsDiv = createSuggestedActions(suggestedAction);
			if (actionsDiv) {
				contentDiv.appendChild(actionsDiv);
			}
		}

		messagesWrapper.appendChild(messageDiv);
		scrollToBottom();
	};

	// Add image message
	const addImageMessage = (type, imageUrl) => {
		if (!messagesWrapper) return;

		const messageDiv = document.createElement('div');
		messageDiv.className = `message ${type}`;

		const avatar = document.createElement('div');
		avatar.className = 'message-avatar';
		avatar.textContent = type === 'user' ? 'U' : 'AI';

		const contentDiv = document.createElement('div');
		contentDiv.className = 'message-content';

		const img = document.createElement('img');
		img.src = imageUrl;
		img.className = 'message-image';
		img.alt = 'Uploaded image';
		img.onclick = () => window.open(imageUrl, '_blank');

		contentDiv.appendChild(img);
		messageDiv.appendChild(avatar);
		messageDiv.appendChild(contentDiv);

		messagesWrapper.appendChild(messageDiv);
		scrollToBottom();
	};

	// Create suggested actions UI
	const createSuggestedActions = (action) => {
		if (!action || !action.action) return null;

		const actionsDiv = document.createElement('div');
		actionsDiv.className = 'suggested-actions';

		const title = document.createElement('div');
		title.className = 'suggested-actions-title';
		title.textContent = 'Suggested Action';

		const buttonsDiv = document.createElement('div');
		buttonsDiv.className = 'suggested-actions-buttons';

		const executeBtn = document.createElement('button');
		executeBtn.className = 'action-btn primary';
		executeBtn.textContent = `Execute: ${action.action}`;
		executeBtn.onclick = () => executeAction(action);

		buttonsDiv.appendChild(executeBtn);
		actionsDiv.appendChild(title);
		actionsDiv.appendChild(buttonsDiv);

		return actionsDiv;
	};

	// Execute action
	const executeAction = async (action) => {
		console.log('Executing action:', action);
		showNotification('Executing action...', 'info');

		try {
			// Call the appropriate handler function based on action type
			if (action.action === 'create_document') {
				await handleCreateDocument(action);
			} else if (action.action === 'dynamic_search') {
				await handleDynamicSearch(action);
			} else if (action.action === 'get_document_details' || action.action === 'get_customer_details') {
				await handleGetDocumentDetails(action);
			} else if (action.action === 'find_duplicates' || action.action === 'find_duplicate_customers') {
				await handleFindDuplicates(action);
			} else if (action.action === 'count_documents' || action.action === 'count_customers') {
				await handleCountDocuments(action);
			} else if (action.action === 'get_customers_by_order_count') {
				await handleGetCustomersByOrderCount(action);
			} else if (action.action === 'get_customers_by_order_value') {
				await handleGetCustomersByOrderValue(action);
			} else if (action.action === 'get_orders_by_customer_group') {
				await handleGetOrdersByCustomerGroup(action);
			} else if (action.action === 'get_orders_by_territory') {
				await handleGetOrdersByTerritory(action);
			} else if (action.action === 'get_orders_by_item') {
				await handleGetOrdersByItem(action);
			} else if (action.action === 'get_orders_with_most_items') {
				await handleGetOrdersWithMostItems(action);
			} else if (action.action === 'get_orders_by_item_group') {
				await handleGetOrdersByItemGroup(action);
			} else if (action.action === 'get_total_quantity_sold') {
				await handleGetTotalQuantitySold(action);
			} else if (action.action === 'get_most_sold_items') {
				await handleGetMostSoldItems(action);
			} else if (action.action === 'get_sales_person_summary') {
				await handleGetSalesPersonSummary(action);
			} else if (action.action === 'get_sales_person_count') {
				await handleGetSalesPersonCount(action);
			} else if (action.action === 'get_sales_person_names') {
				await handleGetSalesPersonNames(action);
			} else if (action.action === 'search_customer') {
				await handleSearchCustomer(action);
			} else {
				throw new Error(`Unknown action type: ${action.action}`);
			}
		} catch (error) {
			console.error('Action execution error:', error);
			showNotification('Failed to execute action', 'error');
			addMessage('ai', `❌ Error: ${error.message || 'Failed to execute action'}`);
		}
	};

	// Format action result
	const formatActionResult = (data) => {
		if (data.results && Array.isArray(data.results)) {
			let html = '<div>';

			if (data.message) {
				html += `<p><strong>${escapeHtml(data.message)}</strong></p>`;
			}

			if (data.results.length > 0) {
				html += '<ul>';
				data.results.slice(0, 10).forEach(item => {
					const name = item.name || item.customer_name || item.title || 'Unknown';
					html += `<li>${escapeHtml(name)}</li>`;
				});
				html += '</ul>';

				if (data.results.length > 10) {
					html += `<p><em>... and ${data.results.length - 10} more</em></p>`;
				}
			} else {
				html += '<p>No results found.</p>';
			}

			html += '</div>';
			return html;
		}

		if (data.data) {
			let html = '<div>';
			html += `<p><strong>${escapeHtml(data.message || 'Results:')}</strong></p>`;
			html += `<pre><code>${escapeHtml(JSON.stringify(data.data, null, 2))}</code></pre>`;
			html += '</div>';
			return html;
		}

		return `<p>${escapeHtml(data.message || 'Action completed')}</p>`;
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

			// Create a container for the extracted information
			const infoContainer = document.createElement('div');
			infoContainer.style.margin = '12px 0';
			infoContainer.style.padding = '12px';
			infoContainer.style.background = '#f7fafc';
			infoContainer.style.borderRadius = '8px';
			infoContainer.style.border = '1px solid #e2e8f0';

			// Add a label
			const infoLabel = document.createElement('div');
			infoLabel.style.fontSize = '12px';
			infoLabel.style.fontWeight = '600';
			infoLabel.style.color = '#4a5568';
			infoLabel.style.marginBottom = '8px';
			infoLabel.textContent = '📋 Extracted Information:';
			infoContainer.appendChild(infoLabel);

			// Display fields with their values in a nice format
			const fields = action.fields || {};
			const fieldsList = document.createElement('div');
			fieldsList.style.display = 'flex';
			fieldsList.style.flexDirection = 'column';
			fieldsList.style.gap = '6px';

			// Field label mapping for better display
			const fieldLabels = {
				'customer_name': '👤 Customer Name',
				'supplier_name': '👤 Supplier Name',
				'mobile_no': '📱 Mobile Number',
				'phone': '📱 Phone',
				'email_id': '📧 Email',
				'email': '📧 Email',
				'territory': '🌍 Territory',
				'customer_group': '👥 Customer Group',
				'address_line1': '📍 Address',
				'city': '🏙️ City',
				'state': '🗺️ State',
				'country': '🌎 Country',
				'pincode': '📮 Pincode'
			};

			// Display each field with its value
			Object.keys(fields).forEach(fieldKey => {
				const fieldValue = fields[fieldKey];
				if (fieldValue !== null && fieldValue !== undefined && fieldValue !== '') {
					const fieldRow = document.createElement('div');
					fieldRow.style.display = 'flex';
					fieldRow.style.justifyContent = 'space-between';
					fieldRow.style.alignItems = 'center';
					fieldRow.style.padding = '6px 8px';
					fieldRow.style.background = 'white';
					fieldRow.style.borderRadius = '4px';
					fieldRow.style.fontSize = '13px';

					const fieldLabel = document.createElement('span');
					fieldLabel.style.color = '#718096';
					fieldLabel.style.fontWeight = '500';
					fieldLabel.textContent = fieldLabels[fieldKey] || fieldKey.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()) + ':';

					const fieldValueSpan = document.createElement('span');
					fieldValueSpan.style.color = '#2d3748';
					fieldValueSpan.style.fontWeight = '600';
					fieldValueSpan.textContent = String(fieldValue);

					fieldRow.appendChild(fieldLabel);
					fieldRow.appendChild(fieldValueSpan);
					fieldsList.appendChild(fieldRow);
				}
			});

			infoContainer.appendChild(fieldsList);

			const buttonContainer = document.createElement('div');
			buttonContainer.className = 'suggested-action-buttons';
			buttonContainer.style.marginTop = '12px';

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
			actionDiv.appendChild(infoContainer);
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
			const typingId = showTypingIndicator();

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

			hideTypingIndicator(typingId);

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
				addMessage('ai', `${successMessage}${linkText}`);

				// Show success notification
				console.log('✅ Document created successfully:', { doctype, name: docName, result });
			} else {
				// Handle error response
				const errorMessage = result?.message || result?.error || 'Unknown error occurred';
				console.error('❌ Create document failed:', result);
				addMessage('ai', `❌ Error: ${errorMessage}`);
			}
		} catch (error) {
			hideTypingIndicator(typingId);
			console.error('Create document error:', error);
			console.error('Error stack:', error.stack);

			// Show more detailed error message
			const errorMsg = error.message || 'Failed to create document. Please try again.';
			addMessage('ai', `❌ Error: ${errorMsg}`);
			showNotification(errorMsg, 'error');
		}
	};

	// Auto-execute action
	// Store the original user question for context
	let lastUserQuestion = '';

	const autoExecuteAction = (action, originalQuestion = '') => {
		console.log('Auto-executing:', action);
		console.log('Original question:', originalQuestion);
		// Use the passed originalQuestion, or fallback to lastUserQuestion
		const questionToUse = originalQuestion || lastUserQuestion;
		if (originalQuestion) {
			lastUserQuestion = originalQuestion;
		}
		const doctype = action.doctype || 'Customer'; // Default to Customer for backward compatibility

		if (action.action === 'dynamic_search') {
			handleDynamicSearch(action);
		} else if (action.action === 'get_document_details' || action.action === 'get_customer_details') {
			handleGetDocumentDetails(action, questionToUse);
		} else if (action.action === 'find_duplicates' || action.action === 'find_duplicate_customers') {
			handleFindDuplicates(action);
		} else if (action.action === 'count_documents' || action.action === 'count_customers') {
			handleCountDocuments(action);
		} else if (action.action === 'get_customers_by_order_count') {
			handleGetCustomersByOrderCount(action);
		} else if (action.action === 'get_customers_by_order_value') {
			handleGetCustomersByOrderValue(action);
		} else if (action.action === 'get_orders_by_customer_group') {
			handleGetOrdersByCustomerGroup(action);
		} else if (action.action === 'get_orders_by_territory') {
			handleGetOrdersByTerritory(action);
		} else if (action.action === 'get_orders_by_item') {
			handleGetOrdersByItem(action);
		} else if (action.action === 'get_orders_with_most_items') {
			handleGetOrdersWithMostItems(action);
		} else if (action.action === 'get_orders_by_item_group') {
			handleGetOrdersByItemGroup(action);
		} else if (action.action === 'get_total_quantity_sold') {
			handleGetTotalQuantitySold(action);
		} else if (action.action === 'get_most_sold_items') {
			handleGetMostSoldItems(action);
		} else if (action.action === 'get_sales_person_summary') {
			handleGetSalesPersonSummary(action);
		} else if (action.action === 'get_sales_person_count') {
			handleGetSalesPersonCount(action);
		} else if (action.action === 'get_sales_person_names') {
			handleGetSalesPersonNames(action);
		} else if (action.action === 'search_customer') {
			// Legacy support
			handleSearchCustomer(action);
		} else {
			console.warn('Unknown action in autoExecuteAction:', action.action);
			// Fallback: try to use executeAction
			executeAction(action);
		}
	};

	// Handle find duplicates
	const handleFindDuplicates = async (action) => {
		try {
			const typingId = showTypingIndicator();
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

			hideTypingIndicator(typingId);

			if (result.status === 'success') {
				displayDuplicateResults(result);
			} else {
				addMessage('ai', `⚠️ Failed to find duplicates: ${result.message}`);
			}
		} catch (error) {
			hideTypingIndicator(typingId);
			addMessage('ai', '❌ Error finding duplicates. Please try again.');
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

		addMessage('ai', message);
	};

	// Handle count documents
	const handleCountDocuments = async (action) => {
		try {
			const typingId = showTypingIndicator();
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
			hideTypingIndicator(typingId);

			if (result.status === 'success') {
				// Store document names in context for follow-up questions
				if (result.document_names && result.document_names.length > 0) {
					// Store in a global context variable for the AI to reference
					window.lastQueryContext = {
						doctype: doctype,
						count: result.total_count,
						document_names: result.document_names,
						first_result: result.first_result || null
					};
				}
				displayCustomerCount(result, doctype);
			} else {
				addMessage('ai', `❌ ${result.message}`);
			}
		} catch (error) {
			hideTypingIndicator(typingId);
			showNotification(`Failed to count ${doctype.toLowerCase()}s. Please try again.`, 'error');
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

		// If document names are available (for small counts), include them in the message
		// This helps the AI understand context for follow-up questions
		if (result.document_names && result.document_names.length > 0) {
			if (result.document_names.length === 1) {
				message += `<p style="margin-top: 8px; color: #4b5563;">The ${doctypeLabel.slice(0, -1)} is: <strong>${escapeHtml(result.document_names[0])}</strong></p>`;
			} else if (result.document_names.length <= 5) {
				message += `<p style="margin-top: 8px; color: #4b5563;">${doctypeLabel.charAt(0).toUpperCase() + doctypeLabel.slice(1)}: ${result.document_names.map(name => `<strong>${escapeHtml(name)}</strong>`).join(', ')}</p>`;
			}
		}

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

		addMessage('ai', message);
	};

	// Handle dynamic search with filters
	const handleDynamicSearch = async (action) => {
		try {
			const typingId = showTypingIndicator();
			const doctype = action?.doctype || 'Customer';

			const formData = new FormData();
			formData.append('doctype', doctype);
			formData.append('filters', JSON.stringify(action.filters || {}));
			formData.append('limit', action?.limit || '20');
			if (action?.order_by) {
				formData.append('order_by', action.order_by);
			}

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

			hideTypingIndicator(typingId);

			if (result.status === 'success') {
				displayDynamicSearchResults(result, doctype);
			} else {
				addMessage('ai', `⚠️ Search failed: ${result.message}`);
			}
		} catch (error) {
			hideTypingIndicator(typingId);
			addMessage('ai', '❌ Search error. Please try again.');
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
		const documentNames = []; // Store document names for context

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
				} else if (detectedDoctype === 'Sales Order') {
					itemName = item.name || 'Unknown';
					itemUrl = `${window.location.origin}/app/sales-order/${encodeURIComponent(item.name)}`;
				} else {
					itemName = item.name || item[`${detectedDoctype.toLowerCase()}_name`] || 'Unknown';
					itemUrl = `${window.location.origin}/app/${detectedDoctype.toLowerCase().replace(/\s+/g, '-')}/${encodeURIComponent(item.name)}`;
				}

				// Store document name for context
				if (item.name) {
					documentNames.push(item.name);
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
				} else if (detectedDoctype === 'Sales Order') {
					// Highlight grand_total prominently for Sales Orders
					if (item.grand_total !== undefined && item.grand_total !== null) {
						details.push(`<span style="color: #3b82f6; font-weight: 600; font-size: 15px;">💰 ${escapeHtml(item.currency || '')} ${escapeHtml(item.grand_total)}</span>`);
					}
					if (item.customer_name) details.push(`<span style="color: #4b5563;">Customer: ${escapeHtml(item.customer_name)}</span>`);
					if (item.transaction_date) details.push(`<span style="color: #4b5563;">Date: ${escapeHtml(item.transaction_date)}</span>`);
					if (item.status) {
						const statusColor = item.status === 'Draft' ? '#f59e0b' : item.status === 'Completed' ? '#10b981' : '#6b7280';
						details.push(`<span style="color: ${statusColor};">Status: ${escapeHtml(item.status)}</span>`);
					}
					if (item.company) details.push(`<span style="color: #4b5563;">Company: ${escapeHtml(item.company)}</span>`);
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

			// Store document names in context for follow-up questions
			if (documentNames.length > 0) {
				window.lastQueryContext = {
					doctype: detectedDoctype,
					count: result.count,
					document_names: documentNames,
					first_result: results.length === 1 ? results[0] : null
				};

				// Add explicit text for AI to parse (hidden visually but in message text)
				// This helps the AI extract document names from the conversation
				if (documentNames.length === 1) {
					message += `<p style="display: none;">Document name: ${documentNames[0]}</p>`;
				} else {
					message += `<p style="display: none;">Document names: ${documentNames.join(', ')}</p>`;
				}
			}
		} else {
			message = `<p>I couldn't find any ${doctypeLabel} matching your search criteria.</p><p style="margin-top: 8px; color: #6b7280;">💡 Try adjusting your search terms or filters.</p>`;
		}

		addMessage('ai', message);
	};

	// Handle get customers by order count
	const handleGetCustomersByOrderCount = async (action) => {
		try {
			const typingId = showTypingIndicator();
			const limit = action?.limit || 10;

			const formData = new FormData();
			formData.append('limit', limit);
			if (action?.order_by) {
				formData.append('order_by', action.order_by);
			}

			const response = await fetch('/api/method/exim_backend.api.ai_chat.get_customers_by_order_count', {
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
			hideTypingIndicator(typingId);

			if (result.status === 'success' && result.results) {
				let message = `<p><strong>Top ${result.count} customers by order count:</strong></p><div style="margin-top: 12px;">`;
				result.results.forEach((item, index) => {
					message += `<div style="margin-bottom: 12px; padding-bottom: 12px; border-bottom: 1px solid #e5e7eb;">`;
					message += `<div style="font-weight: 600; font-size: 15px; color: #1f2937; margin-bottom: 6px;">${escapeHtml(item.customer_name || item.customer)}</div>`;
					const details = [];
					details.push(`<span style="color: #3b82f6; font-weight: 600;">📦 ${item.order_count} orders</span>`);
					if (item.total_value) {
						details.push(`<span style="color: #4b5563;">💰 ${escapeHtml(item.currency || '')} ${escapeHtml(item.total_value)}</span>`);
					}
					if (item.last_order_date) {
						details.push(`<span style="color: #4b5563;">📅 Last order: ${escapeHtml(item.last_order_date)}</span>`);
					}
					message += `<div style="font-size: 13px; line-height: 1.5;">${details.join(' <span style="color: #9ca3af;">•</span> ')}</div>`;
					message += `</div>`;
				});
				message += '</div>';
				addMessage('ai', message);
			} else {
				addMessage('ai', `❌ ${result.message || 'Failed to get customers by order count'}`);
			}
		} catch (error) {
			hideTypingIndicator(typingId);
			addMessage('ai', '❌ Error fetching customers by order count. Please try again.', 'ai');
			console.error('Get customers by order count error:', error);
		}
	};

	// Handle get customers by order value
	const handleGetCustomersByOrderValue = async (action) => {
		try {
			const typingId = showTypingIndicator();
			const limit = action?.limit || 10;

			const formData = new FormData();
			formData.append('limit', limit);
			if (action?.order_by) {
				formData.append('order_by', action.order_by);
			}

			const response = await fetch('/api/method/exim_backend.api.ai_chat.get_customers_by_order_value', {
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
			hideTypingIndicator(typingId);

			if (result.status === 'success' && result.results) {
				let message = `<p><strong>Top ${result.count} customers by order value:</strong></p><div style="margin-top: 12px;">`;
				result.results.forEach((item, index) => {
					message += `<div style="margin-bottom: 12px; padding-bottom: 12px; border-bottom: 1px solid #e5e7eb;">`;
					message += `<div style="font-weight: 600; font-size: 15px; color: #1f2937; margin-bottom: 6px;">${escapeHtml(item.customer_name || item.customer)}</div>`;
					const details = [];
					details.push(`<span style="color: #3b82f6; font-weight: 600; font-size: 15px;">💰 ${escapeHtml(item.currency || '')} ${escapeHtml(item.total_value)}</span>`);
					if (item.order_count) {
						details.push(`<span style="color: #4b5563;">📦 ${item.order_count} orders</span>`);
					}
					if (item.avg_order_value) {
						details.push(`<span style="color: #4b5563;">📊 Avg: ${escapeHtml(item.currency || '')} ${escapeHtml(item.avg_order_value)}</span>`);
					}
					if (item.last_order_date) {
						details.push(`<span style="color: #4b5563;">📅 Last order: ${escapeHtml(item.last_order_date)}</span>`);
					}
					message += `<div style="font-size: 13px; line-height: 1.5;">${details.join(' <span style="color: #9ca3af;">•</span> ')}</div>`;
					message += `</div>`;
				});
				message += '</div>';
				addMessage('ai', message);
			} else {
				addMessage('ai', `❌ ${result.message || 'Failed to get customers by order value'}`);
			}
		} catch (error) {
			hideTypingIndicator(typingId);
			addMessage('ai', '❌ Error fetching customers by order value. Please try again.', 'ai');
			console.error('Get customers by order value error:', error);
		}
	};

	// Handle get orders by customer group
	const handleGetOrdersByCustomerGroup = async (action) => {
		try {
			const typingId = showTypingIndicator();
			const customer_group = action?.customer_group;

			if (!customer_group) {
				hideTypingIndicator(typingId);
				addMessage('ai', '❌ Customer group is required', 'ai');
				return;
			}

			const formData = new FormData();
			formData.append('customer_group', customer_group);

			const response = await fetch('/api/method/exim_backend.api.ai_chat.get_orders_by_customer_group', {
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
			hideTypingIndicator(typingId);

			if (result.status === 'success') {
				// Use the same display function as dynamic search
				displayDynamicSearchResults(result, 'Sales Order');
			} else {
				addMessage('ai', `❌ ${result.message || 'Failed to get orders by customer group'}`);
			}
		} catch (error) {
			hideTypingIndicator(typingId);
			addMessage('ai', '❌ Error fetching orders by customer group. Please try again.', 'ai');
			console.error('Get orders by customer group error:', error);
		}
	};

	// Handle get orders by territory
	const handleGetOrdersByTerritory = async (action) => {
		try {
			const typingId = showTypingIndicator();
			const territory = action?.territory;

			if (!territory) {
				hideTypingIndicator(typingId);
				addMessage('ai', '❌ Territory is required', 'ai');
				return;
			}

			const formData = new FormData();
			formData.append('territory', territory);

			const response = await fetch('/api/method/exim_backend.api.ai_chat.get_orders_by_territory', {
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
			hideTypingIndicator(typingId);

			if (result.status === 'success') {
				// Use the same display function as dynamic search
				displayDynamicSearchResults(result, 'Sales Order');
			} else {
				addMessage('ai', `❌ ${result.message || 'Failed to get orders by territory'}`);
			}
		} catch (error) {
			hideTypingIndicator(typingId);
			addMessage('ai', '❌ Error fetching orders by territory. Please try again.', 'ai');
			console.error('Get orders by territory error:', error);
		}
	};

	// Handle get orders by item
	const handleGetOrdersByItem = async (action) => {
		try {
			const typingId = showTypingIndicator();
			const item_code = action?.item_code;

			if (!item_code) {
				hideTypingIndicator(typingId);
				addMessage('ai', '❌ Item code is required', 'ai');
				return;
			}

			const formData = new FormData();
			formData.append('item_code', item_code);

			const response = await fetch('/api/method/exim_backend.api.ai_chat.get_orders_by_item', {
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
			hideTypingIndicator(typingId);

			if (result.status === 'success') {
				// Use the same display function as dynamic search
				displayDynamicSearchResults(result, 'Sales Order');
			} else {
				addMessage('ai', `❌ ${result.message || 'Failed to get orders by item'}`);
			}
		} catch (error) {
			hideTypingIndicator(typingId);
			addMessage('ai', '❌ Error fetching orders by item. Please try again.', 'ai');
			console.error('Get orders by item error:', error);
		}
	};

	// Handle get orders with most items
	const handleGetOrdersWithMostItems = async (action) => {
		try {
			const typingId = showTypingIndicator();
			const limit = action?.limit || 10;

			const formData = new FormData();
			formData.append('limit', limit);
			if (action?.order_by) {
				formData.append('order_by', action.order_by);
			}

			const response = await fetch('/api/method/exim_backend.api.ai_chat.get_orders_with_most_items', {
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
			hideTypingIndicator(typingId);

			if (result.status === 'success' && result.sales_orders) {
				let message = `<p><strong>Top ${result.count} sales orders with most items:</strong></p><div style="margin-top: 12px;">`;
				result.sales_orders.forEach((item, index) => {
					message += `<div style="margin-bottom: 12px; padding-bottom: 12px; border-bottom: 1px solid #e5e7eb;">`;
					message += `<div style="font-weight: 600; font-size: 15px; color: #1f2937; margin-bottom: 6px;">${escapeHtml(item.name)}</div>`;
					const details = [];
					details.push(`<span style="color: #3b82f6; font-weight: 600;">📦 ${item.item_count} items</span>`);
					if (item.customer_name) {
						details.push(`<span style="color: #4b5563;">Customer: ${escapeHtml(item.customer_name)}</span>`);
					}
					if (item.grand_total) {
						details.push(`<span style="color: #4b5563;">💰 ${escapeHtml(item.currency || '')} ${escapeHtml(item.grand_total)}</span>`);
					}
					if (item.transaction_date) {
						details.push(`<span style="color: #4b5563;">📅 ${escapeHtml(item.transaction_date)}</span>`);
					}
					message += `<div style="font-size: 13px; line-height: 1.5;">${details.join(' <span style="color: #9ca3af;">•</span> ')}</div>`;
					message += `<a href="${window.location.origin}/app/sales-order/${encodeURIComponent(item.name)}" target="_blank" style="color: #3b82f6; text-decoration: none; font-size: 13px; font-weight: 500;">View Sales Order →</a>`;
					message += `</div>`;
				});
				message += '</div>';
				addMessage('ai', message);
			} else {
				addMessage('ai', `❌ ${result.message || 'Failed to get orders with most items'}`);
			}
		} catch (error) {
			hideTypingIndicator(typingId);
			addMessage('ai', '❌ Error fetching orders with most items. Please try again.', 'ai');
			console.error('Get orders with most items error:', error);
		}
	};

	// Handle get orders by item group
	const handleGetOrdersByItemGroup = async (action) => {
		try {
			const typingId = showTypingIndicator();
			const item_group = action?.item_group;

			if (!item_group) {
				hideTypingIndicator(typingId);
				addMessage('ai', '❌ Item group is required', 'ai');
				return;
			}

			const formData = new FormData();
			formData.append('item_group', item_group);

			const response = await fetch('/api/method/exim_backend.api.ai_chat.get_orders_by_item_group', {
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
			hideTypingIndicator(typingId);

			if (result.status === 'success') {
				// Use the same display function as dynamic search
				displayDynamicSearchResults(result, 'Sales Order');
			} else {
				addMessage('ai', `❌ ${result.message || 'Failed to get orders by item group'}`);
			}
		} catch (error) {
			hideTypingIndicator(typingId);
			addMessage('ai', '❌ Error fetching orders by item group. Please try again.', 'ai');
			console.error('Get orders by item group error:', error);
		}
	};

	// Handle get total quantity sold
	const handleGetTotalQuantitySold = async (action) => {
		try {
			const typingId = showTypingIndicator();
			const item_code = action?.item_code;

			if (!item_code) {
				hideTypingIndicator(typingId);
				addMessage('ai', '❌ Item code is required', 'ai');
				return;
			}

			const formData = new FormData();
			formData.append('item_code', item_code);
			if (action?.from_date) {
				formData.append('from_date', action.from_date);
			}
			if (action?.to_date) {
				formData.append('to_date', action.to_date);
			}

			const response = await fetch('/api/method/exim_backend.api.ai_chat.get_total_quantity_sold', {
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
			hideTypingIndicator(typingId);

			if (result.status === 'success') {
				let message = `<p><strong>Total quantity sold for ${escapeHtml(result.item_name || result.item_code)}:</strong></p>`;
				message += `<div style="margin-top: 12px; padding: 12px; background-color: #f3f4f6; border-radius: 8px;">`;
				message += `<div style="font-size: 24px; font-weight: 700; color: #3b82f6; margin-bottom: 8px;">${escapeHtml(result.total_qty || 0)} units</div>`;
				const details = [];
				if (result.total_amount) {
					details.push(`<span style="color: #4b5563;">💰 Total Value: ${escapeHtml(result.total_amount)}</span>`);
				}
				if (result.order_count) {
					details.push(`<span style="color: #4b5563;">📦 Orders: ${escapeHtml(result.order_count)}</span>`);
				}
				if (result.from_date || result.to_date) {
					const dateRange = [];
					if (result.from_date) dateRange.push(`From: ${escapeHtml(result.from_date)}`);
					if (result.to_date) dateRange.push(`To: ${escapeHtml(result.to_date)}`);
					if (dateRange.length > 0) {
						details.push(`<span style="color: #4b5563;">📅 ${dateRange.join(' - ')}</span>`);
					}
				}
				if (details.length > 0) {
					message += `<div style="font-size: 13px; line-height: 1.5; margin-top: 8px;">${details.join(' <span style="color: #9ca3af;">•</span> ')}</div>`;
				}
				message += `</div>`;
				addMessage('ai', message);
			} else {
				addMessage('ai', `❌ ${result.message || 'Failed to get total quantity sold'}`);
			}
		} catch (error) {
			hideTypingIndicator(typingId);
			addMessage('ai', '❌ Error fetching total quantity sold. Please try again.', 'ai');
			console.error('Get total quantity sold error:', error);
		}
	};

	// Handle get most sold items
	const handleGetMostSoldItems = async (action) => {
		try {
			const typingId = showTypingIndicator();
			const limit = action?.limit || 10;

			const formData = new FormData();
			formData.append('limit', limit);
			if (action?.order_by) {
				formData.append('order_by', action.order_by);
			}
			if (action?.from_date) {
				formData.append('from_date', action.from_date);
			}
			if (action?.to_date) {
				formData.append('to_date', action.to_date);
			}

			const response = await fetch('/api/method/exim_backend.api.ai_chat.get_most_sold_items', {
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
			hideTypingIndicator(typingId);

			if (result.status === 'success' && result.results) {
				let message = `<p><strong>Top ${result.count} most sold items:</strong></p><div style="margin-top: 12px;">`;
				result.results.forEach((item, index) => {
					message += `<div style="margin-bottom: 12px; padding-bottom: 12px; border-bottom: 1px solid #e5e7eb;">`;
					message += `<div style="font-weight: 600; font-size: 15px; color: #1f2937; margin-bottom: 6px;">${escapeHtml(item.item_name || item.item_code)}</div>`;
					const details = [];
					details.push(`<span style="color: #3b82f6; font-weight: 600;">📦 ${escapeHtml(item.total_qty || 0)} units sold</span>`);
					if (item.total_amount) {
						details.push(`<span style="color: #4b5563;">💰 ${escapeHtml(item.total_amount)}</span>`);
					}
					if (item.order_count) {
						details.push(`<span style="color: #4b5563;">📋 ${escapeHtml(item.order_count)} orders</span>`);
					}
					if (item.avg_rate) {
						details.push(`<span style="color: #4b5563;">💵 Avg Rate: ${escapeHtml(item.avg_rate)}</span>`);
					}
					message += `<div style="font-size: 13px; line-height: 1.5;">${details.join(' <span style="color: #9ca3af;">•</span> ')}</div>`;
					message += `</div>`;
				});
				message += '</div>';
				addMessage('ai', message);
			} else {
				addMessage('ai', `❌ ${result.message || 'Failed to get most sold items'}`);
			}
		} catch (error) {
			hideTypingIndicator(typingId);
			addMessage('ai', '❌ Error fetching most sold items. Please try again.', 'ai');
			console.error('Get most sold items error:', error);
		}
	};

	// Handle get sales person summary
	const handleGetSalesPersonSummary = async (action) => {
		let typingId;
		try {
			typingId = showTypingIndicator();
			const sales_person = action?.sales_person;

			if (!sales_person) {
				hideTypingIndicator(typingId);
				addMessage('ai', '❌ Sales person name is required');
				return;
			}

			const formData = new FormData();
			formData.append('sales_person', sales_person);

			const response = await fetch('/api/method/exim_backend.api.ai_chat.get_sales_person_summary', {
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
			console.log('📊 Sales Person Summary API Response:', responseData);
			const result = responseData.message || responseData;
			console.log('📊 Parsed result:', result);
			hideTypingIndicator(typingId);

			if (result.status === 'success' && result.summary) {
				const summary = result.summary;
				let message = `<div style="max-width: 100%;">`;
				message += `<h3 style="margin-bottom: 16px; color: #1f2937; font-size: 18px; font-weight: 600;">📊 Sales Person Summary: ${escapeHtml(summary.sales_person_name || sales_person)}</h3>`;

				// Basic Info
				message += `<div style="margin-bottom: 20px; padding: 16px; background: #f9fafb; border-radius: 8px;">`;
				message += `<h4 style="margin-bottom: 12px; color: #374151; font-size: 15px; font-weight: 600;">Basic Information</h4>`;
				message += `<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; font-size: 14px;">`;
				if (summary.employee) message += `<div><strong>Employee:</strong> ${escapeHtml(summary.employee)}</div>`;
				if (summary.department) message += `<div><strong>Department:</strong> ${escapeHtml(summary.department)}</div>`;
				message += `<div><strong>Status:</strong> ${summary.enabled ? '✅ Enabled' : '❌ Disabled'}</div>`;
				if (summary.commission_rate) message += `<div><strong>Commission Rate:</strong> ${escapeHtml(summary.commission_rate)}</div>`;
				message += `</div></div>`;

				// Sales Orders
				message += `<div style="margin-bottom: 20px; padding: 16px; background: #eff6ff; border-radius: 8px; border-left: 4px solid #3b82f6;">`;
				message += `<h4 style="margin-bottom: 12px; color: #1e40af; font-size: 15px; font-weight: 600;">📦 Sales Orders</h4>`;
				message += `<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; font-size: 14px;">`;
				message += `<div><strong>Submitted:</strong> <span style="color: #3b82f6; font-weight: 600;">${summary.sales_order_count || 0}</span></div>`;
				message += `<div><strong>Draft:</strong> <span style="color: #6b7280;">${summary.draft_sales_order_count || 0}</span></div>`;
				message += `<div><strong>Total:</strong> <span style="font-weight: 600;">${summary.total_sales_order_count || 0}</span></div>`;
				if (summary.total_sales_order_amount) {
					message += `<div><strong>Total Amount:</strong> <span style="color: #059669; font-weight: 600;">${escapeHtml(summary.total_sales_order_amount.toLocaleString())}</span></div>`;
				}
				message += `</div></div>`;

				// Sales Invoices
				message += `<div style="margin-bottom: 20px; padding: 16px; background: #f0fdf4; border-radius: 8px; border-left: 4px solid #10b981;">`;
				message += `<h4 style="margin-bottom: 12px; color: #047857; font-size: 15px; font-weight: 600;">🧾 Sales Invoices</h4>`;
				message += `<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; font-size: 14px;">`;
				message += `<div><strong>Submitted:</strong> <span style="color: #10b981; font-weight: 600;">${summary.sales_invoice_count || 0}</span></div>`;
				message += `<div><strong>Draft:</strong> <span style="color: #6b7280;">${summary.draft_sales_invoice_count || 0}</span></div>`;
				message += `<div><strong>Total:</strong> <span style="font-weight: 600;">${summary.total_sales_invoice_count || 0}</span></div>`;
				if (summary.total_sales_amount) {
					message += `<div><strong>Total Amount:</strong> <span style="color: #059669; font-weight: 600;">${escapeHtml(summary.total_sales_amount.toLocaleString())}</span></div>`;
				}
				message += `</div></div>`;

				// Financial Summary
				message += `<div style="margin-bottom: 20px; padding: 16px; background: #fef3c7; border-radius: 8px; border-left: 4px solid #f59e0b;">`;
				message += `<h4 style="margin-bottom: 12px; color: #92400e; font-size: 15px; font-weight: 600;">💰 Financial Summary</h4>`;
				message += `<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; font-size: 14px;">`;
				if (summary.outstanding_amount) {
					message += `<div><strong>Outstanding:</strong> <span style="color: #dc2626; font-weight: 600;">${escapeHtml(summary.outstanding_amount.toLocaleString())}</span></div>`;
				}
				if (summary.paid_amount) {
					message += `<div><strong>Paid:</strong> <span style="color: #059669; font-weight: 600;">${escapeHtml(summary.paid_amount.toLocaleString())}</span></div>`;
				}
				if (summary.total_commission_earned) {
					message += `<div><strong>Commission Earned:</strong> <span style="color: #7c3aed; font-weight: 600;">${escapeHtml(summary.total_commission_earned.toLocaleString())}</span></div>`;
				}
				message += `</div></div>`;

				// Performance Metrics
				message += `<div style="margin-bottom: 20px; padding: 16px; background: #f3e8ff; border-radius: 8px; border-left: 4px solid #8b5cf6;">`;
				message += `<h4 style="margin-bottom: 12px; color: #6b21a8; font-size: 15px; font-weight: 600;">📈 Performance Metrics</h4>`;
				message += `<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; font-size: 14px;">`;
				message += `<div><strong>Unique Customers:</strong> <span style="font-weight: 600;">${summary.unique_customers || 0}</span></div>`;
				if (summary.average_order_value) {
					message += `<div><strong>Avg Order Value:</strong> <span style="font-weight: 600;">${escapeHtml(summary.average_order_value.toLocaleString())}</span></div>`;
				}
				if (summary.average_invoice_value) {
					message += `<div><strong>Avg Invoice Value:</strong> <span style="font-weight: 600;">${escapeHtml(summary.average_invoice_value.toLocaleString())}</span></div>`;
				}
				if (summary.conversion_rate) {
					message += `<div><strong>Conversion Rate:</strong> <span style="font-weight: 600;">${escapeHtml(summary.conversion_rate.toFixed(1))}%</span></div>`;
				}
				message += `</div></div>`;

				// Recent Activity
				if (summary.recent_orders && summary.recent_orders.length > 0) {
					message += `<div style="margin-bottom: 20px;">`;
					message += `<h4 style="margin-bottom: 12px; color: #374151; font-size: 15px; font-weight: 600;">🕒 Recent Orders</h4>`;
					summary.recent_orders.slice(0, 5).forEach(order => {
						message += `<div style="padding: 8px; margin-bottom: 8px; background: #f9fafb; border-radius: 4px; font-size: 13px;">`;
						message += `<strong>${escapeHtml(order.name)}</strong> - ${escapeHtml(order.customer_name || order.customer)} - ${escapeHtml(order.transaction_date || '')}`;
						if (order.grand_total) {
							message += ` - <span style="color: #059669; font-weight: 600;">${escapeHtml(order.grand_total.toLocaleString())}</span>`;
						}
						message += `</div>`;
					});
					message += `</div>`;
				}

				message += `</div>`;
				console.log('📊 Adding message to chat');
				addMessage('ai', message);
			} else {
				console.log('❌ Result status or summary missing:', {
					status: result.status,
					hasSummary: !!result.summary,
					result: result
				});
				addMessage('ai', `❌ ${result.message || 'Failed to get sales person summary. Response: ' + JSON.stringify(result)}`);
			}
		} catch (error) {
			if (typingId) hideTypingIndicator(typingId);
			console.error('❌ Get sales person summary error:', error);
			console.error('❌ Error stack:', error.stack);
			addMessage('ai', `❌ Error fetching sales person summary: ${error.message || 'Unknown error'}. Please try again.`);
		}
	};

	// Handle get sales person count
	const handleGetSalesPersonCount = async (action) => {
		let typingId;
		try {
			typingId = showTypingIndicator();

			const formData = new FormData();
			if (action?.filters) {
				formData.append('filters', JSON.stringify(action.filters));
			}

			const response = await fetch('/api/method/exim_backend.api.ai_chat.get_sales_person_count', {
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
			hideTypingIndicator(typingId);

			if (result.status === 'success') {
				addMessage('ai', `📊 Total Sales Persons: <strong>${result.total_count || 0}</strong>`);
			} else {
				addMessage('ai', `❌ ${result.message || 'Failed to get sales person count'}`);
			}
		} catch (error) {
			hideTypingIndicator(typingId);
			addMessage('ai', '❌ Error fetching sales person count. Please try again.', 'ai');
			console.error('Get sales person count error:', error);
		}
	};

	// Handle get sales person names
	const handleGetSalesPersonNames = async (action) => {
		let typingId;
		try {
			typingId = showTypingIndicator();

			const formData = new FormData();
			if (action?.filters) {
				formData.append('filters', JSON.stringify(action.filters));
			}
			if (action?.limit) {
				formData.append('limit', action.limit);
			}

			const response = await fetch('/api/method/exim_backend.api.ai_chat.get_sales_person_names', {
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
			hideTypingIndicator(typingId);

			if (result.status === 'success' && result.names) {
				let message = `<p><strong>Sales Person Names (${result.count}):</strong></p><ul style="margin-top: 12px;">`;
				result.names.forEach(name => {
					message += `<li style="margin-bottom: 6px;">${escapeHtml(name)}</li>`;
				});
				message += '</ul>';
				addMessage('ai', message);
			} else {
				addMessage('ai', `❌ ${result.message || 'Failed to get sales person names'}`);
			}
		} catch (error) {
			hideTypingIndicator(typingId);
			addMessage('ai', '❌ Error fetching sales person names. Please try again.', 'ai');
			console.error('Get sales person names error:', error);
		}
	};

	// Handle search customer
	const handleSearchCustomer = async (action) => {
		try {
			const typingId = showTypingIndicator();

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
			hideTypingIndicator(typingId);

			if (result.status === 'success') {
				displayCustomerSearchResults(result);
			} else {
				addMessage('ai', `❌ Search failed: ${result.message}`);
			}
		} catch (error) {
			hideTypingIndicator(typingId);
			showNotification('Failed to search customers. Please try again.', 'error');
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

		addMessage('ai', message);
	};

	// Answer user's question based on document data using AI
	const answerQuestionFromDocument = async (document, doctype, question) => {
		try {
			const typingId = showTypingIndicator();

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
- IMPORTANT: If the data shows a value (even if it's 0), provide that value directly. Don't say you can't find it.
- CRITICAL: Use plain text format. DO NOT use markdown formatting like **bold**, *italic*, or special characters like * or **. Just provide clean, readable text.`;

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

			hideTypingIndicator(typingId);

			// The process_chat API returns: {status: "success", message: "AI response", ...}
			if (result && (result.status === 'success' || result.message)) {
				const aiAnswer = result.message || 'No answer provided';
				// Clean the answer (remove JSON code blocks if present)
				let cleanAnswer = aiAnswer.replace(/```json[\s\S]*?```/g, '').replace(/```[\s\S]*?```/g, '').trim();
				// Remove any remaining JSON structure if it's just the action
				cleanAnswer = cleanAnswer.replace(/^\s*\{[\s\S]*"action"[\s\S]*\}\s*$/g, '').trim();

				if (cleanAnswer && cleanAnswer.length > 0) {
					// Check if answer contains markdown formatting and convert it
					const hasMarkdown = /[\*\-\+]\s+|\*\*|__|`|```/.test(cleanAnswer);
					if (hasMarkdown) {
						// Convert markdown to HTML
						addMessage(markdownToHtml(cleanAnswer), 'ai', null, result.token_usage);
					} else {
						// Plain text - wrap in paragraph
						addMessage('ai', `<p class="ai-paragraph">${escapeHtml(cleanAnswer)}</p>`, 'ai', null, result.token_usage);
					}
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
			hideTypingIndicator(typingId);
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
			const typingId = showTypingIndicator();
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
			console.log('🔍 Checking result.sales_order:', result?.sales_order);
			console.log('🔍 Type of result.sales_order:', typeof result?.sales_order);
			console.log('🔍 Has sales_order key:', 'sales_order' in (result || {}));
			console.log('═══════════════════════════════════════════════════════');

			hideTypingIndicator(typingId);

			// Validate result exists
			if (!result) {
				console.error('❌ CRITICAL: result is null/undefined!');
				addMessage('ai', `❌ Error: No response received from server.`);
				return;
			}

			// Handle both success and error cases
			if (result.status === 'success') {
				// Support doctype-specific and generic document formats
				// Try different possible keys based on doctype
				let document = null;

				console.log('🔍 Extracting document for doctype:', doctype);
				console.log('🔍 Result keys:', Object.keys(result));

				if (doctype === 'Customer') {
					document = result.customer || result.document;
					console.log('🔍 Customer document found:', !!result.customer);
				} else if (doctype === 'Item') {
					document = result.item || result.document;
					console.log('🔍 Item document found:', !!result.item);
				} else if (doctype === 'Sales Order') {
					// Sales Order uses underscore in API response
					// Try multiple possible keys
					document = result.sales_order || result['sales_order'] || result.salesOrder || result.document;
					console.log('🔍 Sales Order document found:', !!result.sales_order);
					console.log('🔍 result.sales_order:', result.sales_order);
					console.log('🔍 result["sales_order"]:', result['sales_order']);
					console.log('🔍 All result keys:', Object.keys(result || {}));
					if (!document && result) {
						// Try to find any key that contains the sales order data
						for (const key in result) {
							if (key.toLowerCase().includes('sales') || key.toLowerCase().includes('order')) {
								console.log(`🔍 Found potential key: ${key}`, result[key]);
								if (result[key] && typeof result[key] === 'object' && result[key].name) {
									document = result[key];
									console.log(`✅ Using key: ${key}`);
									break;
								}
							}
						}
					}
				} else {
					// Generic: try doctype-specific key first (with underscore), then space, then generic
					const doctypeKeyUnderscore = doctype.toLowerCase().replace(/\s+/g, '_');
					const doctypeKeySpace = doctype.toLowerCase();
					document = result[doctypeKeyUnderscore] || result[doctypeKeySpace] || result.document;
					console.log('🔍 Generic doctype - trying:', doctypeKeyUnderscore, doctypeKeySpace);
				}

				console.log('✅ Extracted document:', document);
				console.log('✅ Document type:', typeof document);
				console.log('✅ Document name:', document?.name);

				// Check if document exists and is a valid object
				if (!document || typeof document !== 'object' || Array.isArray(document)) {
					console.error('Document is invalid. Full result:', result);
					const errorDetails = result.message || 'Document data is missing or invalid';
					addMessage('ai', `❌ ${errorDetails}`);
					return;
				}

				// Validate document has at least a name or identifier
				if (!document.name && !document.item_code && !document[`${doctype.toLowerCase()}_name`]) {
					console.error('Document missing identifier. Document:', document);
					addMessage('ai', `❌ Document data is incomplete. Missing identifier.`);
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
					addMessage('ai', `❌ Error: Invalid document data received from server. Please check console for details.`);
					return;
				}

				// Additional check: ensure document has required properties
				if (doctype === 'Item' && !document.name && !document.item_code && !document.item_name) {
					console.error('Item document missing all identifiers:', document);
					addMessage('ai', `❌ Error: Item document is missing required fields (name, item_code, item_name).`);
					return;
				}

				// If original question exists, send document data to AI to answer the specific question
				// BUT: For "detailed info", "complete info", "details", etc., just display directly without AI formatting
				if (originalQuestion && originalQuestion.trim()) {
					const questionLower = originalQuestion.toLowerCase();
					console.log('🔍 Checking question for info request:', questionLower);
					// Comprehensive detection: If asking for complete/detailed/full info, display directly
					// Check for patterns like "give complete sales order info", "show full details", etc.
					const isInfoRequest =
						questionLower.includes('detailed info') ||
						questionLower.includes('complete info') ||
						questionLower.includes('complete sales order info') ||
						questionLower.includes('complete item info') ||
						questionLower.includes('complete customer info') ||
						questionLower.includes('full info') ||
						questionLower.includes('full details') ||
						questionLower.includes('all details') ||
						questionLower.includes('all info') ||
						questionLower.includes('give complete') ||
						questionLower.includes('show complete') ||
						questionLower.includes('give full') ||
						questionLower.includes('show full') ||
						questionLower.includes('give all') ||
						questionLower.includes('show all') ||
						questionLower.match(/give\s+(complete|full|all|detailed)\s+(sales\s+order|item|customer)?\s*info/i) ||
						questionLower.match(/show\s+(complete|full|all|detailed)\s+(sales\s+order|item|customer)?\s*info/i) ||
						questionLower.match(/give\s+(complete|full|all|detailed)\s+(sales\s+order|item|customer)?\s*details/i) ||
						questionLower.match(/show\s+(complete|full|all|detailed)\s+(sales\s+order|item|customer)?\s*details/i) ||
						(questionLower.includes('info') && (questionLower.includes('complete') || questionLower.includes('full') || questionLower.includes('all'))) ||
						(questionLower.includes('details') && (questionLower.includes('complete') || questionLower.includes('full') || questionLower.includes('all'))) ||
						questionLower.includes('details') ||
						questionLower.includes('show details') ||
						questionLower.includes('give details');

					console.log('🔍 Is info request?', isInfoRequest);

					if (isInfoRequest) {
						console.log('Question asks for complete/detailed info - displaying directly without AI formatting');
						// Display directly using appropriate function
						if (doctype === 'Sales Order') {
							if (typeof displaySalesOrderDetails === 'function') {
								displaySalesOrderDetails(document);
							} else {
								displayDocumentDetails(document, doctype);
							}
						} else if (doctype === 'Customer') {
							if (typeof displayCustomerDetails === 'function') {
								displayCustomerDetails(document);
							} else {
								displayDocumentDetails(document, doctype);
							}
						} else {
							displayDocumentDetails(document, doctype);
						}
					} else {
						// For specific questions, use AI to extract answer
						console.log('Original question detected, sending to AI for intelligent extraction:', originalQuestion);
						await answerQuestionFromDocument(document, doctype, originalQuestion);
					}
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
						} else if (doctype === 'Sales Order') {
							// Final check before calling - document must exist and be valid
							if (!document || typeof document !== 'object') {
								throw new Error(`Document is ${document === null ? 'null' : typeof document} - cannot display`);
							}
							if (typeof displaySalesOrderDetails === 'function') {
								displaySalesOrderDetails(document);
							} else if (typeof displayDocumentDetails === 'function') {
								displayDocumentDetails(document, doctype);
							} else {
								throw new Error('displaySalesOrderDetails function not found');
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
						addMessage('ai', `❌ Error displaying document: ${displayError.message || 'Unknown error'}`);
					}
				}
			} else {
				// Handle error response
				const errorMsg = result.message || 'Unknown error occurred';
				console.error('API returned error status:', result);
				addMessage('ai', `❌ ${errorMsg}`);
			}
		} catch (error) {
			hideTypingIndicator(typingId);
			showNotification('Failed to get document details. Please try again.', 'error');
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

		addMessage('ai', message);
	};

	// Display Sales Order details
	const displaySalesOrderDetails = (salesOrder) => {
		try {
			if (!salesOrder || typeof salesOrder !== 'object') {
				console.error('displaySalesOrderDetails: salesOrder is invalid', salesOrder);
				addMessage('ai', `❌ Error: Sales Order data is missing or invalid.`);
				return;
			}

			const soName = salesOrder.name || 'Unknown';
			const soUrl = `${window.location.origin}/app/sales-order/${encodeURIComponent(soName)}`;

			let message = `<div class="ai-document-details">`;
			message += `<p class="ai-paragraph"><strong>Sales Order: ${escapeHtml(soName)}</strong></p>`;

			// Key Information Section
			message += `<div style="margin: 16px 0; padding: 12px; background: #f9fafb; border-radius: 8px; border-left: 3px solid #3b82f6;">`;

			const keyInfo = [];
			if (salesOrder.customer_name) keyInfo.push(`<span style="color: #374151;"><strong>Customer:</strong> ${escapeHtml(salesOrder.customer_name)}</span>`);
			if (salesOrder.transaction_date) keyInfo.push(`<span style="color: #374151;"><strong>Date:</strong> ${escapeHtml(salesOrder.transaction_date)}</span>`);
			if (salesOrder.delivery_date) keyInfo.push(`<span style="color: #374151;"><strong>Delivery Date:</strong> ${escapeHtml(salesOrder.delivery_date)}</span>`);
			if (salesOrder.status) {
				const statusColor = salesOrder.status === 'Draft' ? '#f59e0b' : salesOrder.status === 'Completed' ? '#10b981' : '#6b7280';
				keyInfo.push(`<span style="color: #374151;"><strong>Status:</strong> <span style="color: ${statusColor};">${escapeHtml(salesOrder.status)}</span></span>`);
			}
			if (salesOrder.company) keyInfo.push(`<span style="color: #374151;"><strong>Company:</strong> ${escapeHtml(salesOrder.company)}</span>`);
			if (salesOrder.grand_total !== undefined) keyInfo.push(`<span style="color: #374151;"><strong>Grand Total:</strong> ${escapeHtml(salesOrder.currency || '')} ${escapeHtml(salesOrder.grand_total)}</span>`);

			message += `<div style="display: flex; flex-wrap: wrap; gap: 12px; font-size: 14px; line-height: 1.6;">${keyInfo.join('')}</div>`;
			message += `</div>`;

			// Items Section
			if (salesOrder.items && Array.isArray(salesOrder.items) && salesOrder.items.length > 0) {
				message += `<div style="margin: 16px 0;">`;
				message += `<p class="ai-paragraph" style="font-weight: 600; color: #111827; margin-bottom: 12px;">Items (${salesOrder.items.length}):</p>`;
				message += `<div style="background: #ffffff; border: 1px solid #e5e7eb; border-radius: 6px; overflow: hidden;">`;

				salesOrder.items.forEach((item, index) => {
					message += `<div style="padding: 12px; ${index < salesOrder.items.length - 1 ? 'border-bottom: 1px solid #e5e7eb;' : ''}">`;
					message += `<div style="display: flex; justify-content: space-between; align-items: start;">`;
					message += `<div style="flex: 1;">`;
					message += `<div style="font-weight: 600; color: #111827; margin-bottom: 4px;">${escapeHtml(item.item_name || item.item_code || 'Unknown Item')}</div>`;
					if (item.description) {
						const descText = item.description.replace(/<[^>]*>/g, '').trim();
						if (descText) {
							message += `<div style="font-size: 13px; color: #6b7280; margin-bottom: 4px;">${escapeHtml(descText)}</div>`;
						}
					}
					message += `<div style="font-size: 13px; color: #6b7280;">Qty: ${escapeHtml(item.qty || 0)} ${escapeHtml(item.uom || item.stock_uom || '')}</div>`;
					message += `</div>`;
					message += `<div style="text-align: right; margin-left: 16px;">`;
					message += `<div style="font-size: 13px; color: #6b7280;">@ ${escapeHtml(salesOrder.currency || '')} ${escapeHtml(item.rate || 0)}</div>`;
					message += `<div style="font-weight: 600; color: #3b82f6; margin-top: 4px;">${escapeHtml(salesOrder.currency || '')} ${escapeHtml(item.amount || 0)}</div>`;
					message += `</div>`;
					message += `</div>`;
					message += `</div>`;
				});

				message += `</div>`;
				message += `</div>`;
			}

			// Totals Section
			if (salesOrder.grand_total !== undefined) {
				message += `<div style="margin: 16px 0; padding: 12px; background: #f9fafb; border-radius: 8px;">`;
				if (salesOrder.net_total !== undefined) {
					message += `<div style="display: flex; justify-content: space-between; margin-bottom: 8px;">`;
					message += `<span style="color: #6b7280;">Subtotal:</span>`;
					message += `<span style="color: #374151; font-weight: 500;">${escapeHtml(salesOrder.currency || '')} ${escapeHtml(salesOrder.net_total || salesOrder.total || 0)}</span>`;
					message += `</div>`;
				}
				if (salesOrder.total_taxes_and_charges > 0) {
					message += `<div style="display: flex; justify-content: space-between; margin-bottom: 8px;">`;
					message += `<span style="color: #6b7280;">Taxes & Charges:</span>`;
					message += `<span style="color: #374151; font-weight: 500;">${escapeHtml(salesOrder.currency || '')} ${escapeHtml(salesOrder.total_taxes_and_charges)}</span>`;
					message += `</div>`;
				}
				message += `<div style="display: flex; justify-content: space-between; padding-top: 8px; border-top: 2px solid #e5e7eb; margin-top: 8px;">`;
				message += `<span style="color: #111827; font-weight: 600; font-size: 16px;">Grand Total:</span>`;
				message += `<span style="color: #3b82f6; font-weight: 700; font-size: 16px;">${escapeHtml(salesOrder.currency || '')} ${escapeHtml(salesOrder.grand_total)}</span>`;
				message += `</div>`;
				message += `</div>`;
			}

			// Payment Schedule
			if (salesOrder.payment_schedule && Array.isArray(salesOrder.payment_schedule) && salesOrder.payment_schedule.length > 0) {
				message += `<div style="margin: 16px 0;">`;
				message += `<p class="ai-paragraph" style="font-weight: 600; color: #111827; margin-bottom: 12px;">Payment Schedule:</p>`;
				message += `<ul class="ai-list">`;
				salesOrder.payment_schedule.forEach(payment => {
					const paymentText = `${escapeHtml(payment.payment_term || 'N/A')} - ${escapeHtml(salesOrder.currency || '')} ${escapeHtml(payment.payment_amount || 0)}`;
					if (payment.due_date) {
						message += `<li>${paymentText} (Due: ${escapeHtml(payment.due_date)})</li>`;
					} else {
						message += `<li>${paymentText}</li>`;
					}
				});
				message += `</ul>`;
				message += `</div>`;
			}

			message += `<div style="margin-top: 16px;"><a href="${soUrl}" target="_blank" style="color: #3b82f6; text-decoration: none; font-size: 13px; font-weight: 500;">View Sales Order →</a></div>`;
			message += '</div>';

			addMessage('ai', message);
		} catch (error) {
			console.error('displaySalesOrderDetails error:', error, { salesOrder });
			addMessage('ai', `❌ Error displaying Sales Order details: ${error.message || 'Unknown error'}`);
		}
	};

	// Display generic document details
	const displayDocumentDetails = (document, doctype) => {
		try {
			// Validate document exists and is a valid object
			if (!document || typeof document !== 'object' || Array.isArray(document)) {
				console.error('displayDocumentDetails: document is invalid', { document, doctype });
				addMessage('ai', `❌ Error: Document data is missing or invalid.`);
				return;
			}

			// Validate doctype
			if (!doctype || typeof doctype !== 'string') {
				console.error('displayDocumentDetails: doctype is invalid', { document, doctype });
				addMessage('ai', `❌ Error: Invalid document type.`);
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

			addMessage('ai', message);
		} catch (error) {
			console.error('displayDocumentDetails error:', error, { document, doctype });
			addMessage('ai', `❌ Error displaying document details: ${error.message || 'Unknown error'}`);
		}
	};

	// Show typing indicator
	const showTypingIndicator = () => {
		if (!messagesWrapper) return null;

		const typingDiv = document.createElement('div');
		typingDiv.className = 'message ai';
		typingDiv.id = 'typing-indicator-' + Date.now();

		const avatar = document.createElement('div');
		avatar.className = 'message-avatar';
		avatar.textContent = 'AI';

		const indicator = document.createElement('div');
		indicator.className = 'typing-indicator active';
		indicator.innerHTML = '<div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>';

		typingDiv.appendChild(avatar);
		typingDiv.appendChild(indicator);
		messagesWrapper.appendChild(typingDiv);
		scrollToBottom();

		return typingDiv.id;
	};

	// Hide typing indicator
	const hideTypingIndicator = (id) => {
		const indicator = document.getElementById(id);
		if (indicator) {
			indicator.remove();
		}
	};

	// Scroll to bottom
	const scrollToBottom = () => {
		if (messagesContainer) {
			messagesContainer.scrollTop = messagesContainer.scrollHeight;
		}
	};

	// Show notification (simple implementation)
	const showNotification = (message, type = 'info') => {
		console.log(`[${type.toUpperCase()}] ${message}`);
	};

	// ============================================================================
	// INTELLIGENT QUERY SYSTEM - DISABLED (COMMENTED OUT)
	// ============================================================================

	/**
	 * Send query to intelligent query system
	 * DISABLED - Commented out to use traditional functional approach
	 * @param {string} query - User's natural language query
	 * @returns {Promise<Object>} - Response from intelligent query API
	 */
	/*
	const sendIntelligentQuery = async (query) => {
		try {
			const formData = new FormData();
			formData.append('query', query);
			formData.append('session_id', sessionId);

			// Get CSRF token from meta tag (same as traditional system)
			const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
			console.log('CSRF token for intelligent query:', csrfToken);

			const response = await fetch(
				'/api/method/exim_backend.api.intelligent_query.process_intelligent_query',
				{
					method: 'POST',
					headers: {
						'X-Frappe-CSRF-Token': csrfToken
					},
					body: formData
				}
			);

			if (!response.ok) {
				throw new Error(`HTTP error! status: ${response.status}`);
			}

			const result = await response.json();
			
			// Check if there's an error in the response
			if (result.message && result.message.status === 'error') {
				throw new Error(result.message.message || 'Query processing failed');
			}

			return result.message || result;
		} catch (error) {
			console.error('Intelligent Query Error:', error);
			console.error('Full error details:', error);
			
			// Don't automatically fallback - show error and let user decide
			// The intelligent query should work for all DocTypes, so if it fails, 
			// we should fix the issue rather than falling back to limited old system
			throw error;
		}
	};
	*/

	/**
	 * Display results from intelligent query system
	 * DISABLED - Commented out to use traditional functional approach
	 * @param {Object} result - Response from intelligent query
	 */
	/*
	const displayIntelligentQueryResults = (result) => {
		const { 
			execution_type, 
			data, 
			ai_reasoning, 
			detected_doctypes, 
			query_metadata,
			status 
		} = result;

		if (status === 'error') {
			addMessage('ai', `❌ ${result.message || 'Query processing failed'}`);
			return;
		}

		let message = '<div style="font-family: system-ui, -apple-system, sans-serif;">';

		// Show AI Reasoning (collapsible)
		if (ai_reasoning) {
			message += `
				<details style="margin-bottom: 16px; padding: 12px; background: #fff9db; border-radius: 8px; border-left: 3px solid #ffc107;">
					<summary style="cursor: pointer; font-weight: 600; color: #856404; display: flex; align-items: center; gap: 8px;">
						💡 AI Reasoning
					</summary>
					<p style="margin-top: 8px; font-size: 14px; color: #856404; line-height: 1.5;">
						${escapeHtml(ai_reasoning)}
					</p>
				</details>
			`;
		}

		// Show Detected DocTypes
		if (detected_doctypes && detected_doctypes.length > 0) {
			message += `
				<div style="margin-bottom: 16px; display: flex; gap: 8px; flex-wrap: wrap; align-items: center;">
					<span style="font-size: 13px; color: #6b7280; font-weight: 500;">DocTypes:</span>
					${detected_doctypes.map(dt => `
						<span style="
							background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
							color: white;
							padding: 4px 12px;
							border-radius: 12px;
							font-size: 12px;
							font-weight: 600;
							box-shadow: 0 2px 4px rgba(0,0,0,0.1);
						">
							${escapeHtml(dt)}
						</span>
					`).join('')}
				</div>
			`;
		}

		// Display Results
		// First, check for get_document_details response (single document)
		// Response format: {status: 'success', customer: {...}, doctype: 'Customer'}
		// Only check for single document if there are NO results array and NO count
		if (data && !data.results && !data.total_count && !data.count && !Array.isArray(data.results)) {
			// Check for doctype-specific keys (customer, item, sales_order, etc.)
			const doctypeKey = data.doctype ? data.doctype.toLowerCase() : null;
			let document = null;
			
			if (doctypeKey && data[doctypeKey]) {
				document = data[doctypeKey];
			} else if (data.document) {
				// Generic "document" key
				document = data.document;
			} else {
				// Try to find any key that looks like a doctype (not status, doctype, etc.)
				const excludedKeys = ['status', 'doctype', 'results', 'total_count', 'count', 'query_executed'];
				for (const key in data) {
					if (!excludedKeys.includes(key) && typeof data[key] === 'object' && data[key] !== null && !Array.isArray(data[key])) {
						document = data[key];
						break;
					}
				}
			}
			
			if (document) {
				// Display single document details
				const doctypeName = data.doctype || detected_doctypes?.[0] || 'Document';
				message += `
					<div style="
						background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
						border-radius: 12px;
						padding: 20px;
						margin-bottom: 16px;
						border: 1px solid #dee2e6;
						box-shadow: 0 2px 8px rgba(0,0,0,0.05);
					">
						<h3 style="
							font-size: 18px;
							font-weight: 700;
							color: #1f2937;
							margin: 0 0 16px 0;
							padding-bottom: 12px;
							border-bottom: 2px solid #667eea;
						">
							${escapeHtml(doctypeName)} Details
						</h3>
				`;
				
				// Display all fields
				const fields = Object.entries(document);
				fields.forEach(([key, value], idx) => {
					// Skip internal fields
					if (key.startsWith('_') || key === 'doctype' || key === 'name') {
						if (key === 'name') {
							// Show name prominently
							message += `
								<div style="font-size: 16px; font-weight: 700; color: #1f2937; margin-bottom: 12px;">
									<span style="color: #4CAF50;">●</span> ${escapeHtml(String(value))}
								</div>
							`;
						}
						return;
					}
					
					// Skip null, undefined, empty objects, and empty arrays
					if (value === null || value === undefined || 
						(Array.isArray(value) && value.length === 0) ||
						(typeof value === 'object' && Object.keys(value).length === 0)) {
						return;
					}
					
					const label = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
					
					// Format value based on type
					let displayValue = value;
					if (Array.isArray(value)) {
						displayValue = value.length + ' item(s)';
					} else if (typeof value === 'object') {
						displayValue = JSON.stringify(value, null, 2);
					} else {
						displayValue = String(value);
					}
					
					message += `
						<div style="font-size: 14px; color: #4b5563; margin-bottom: 8px; padding: 8px; background: white; border-radius: 6px;">
							<span style="color: #9ca3af; font-weight: 600;">${escapeHtml(label)}:</span> 
							<span style="font-weight: 500; color: #1f2937;">${escapeHtml(displayValue)}</span>
						</div>
					`;
				});
				
				// Add "View" link if there's a "name" field
				if (document.name && doctypeName) {
					const docUrl = `/app/${doctypeName.toLowerCase().replace(/ /g, '-')}/${document.name}`;
					message += `
						<div style="margin-top: 16px; padding-top: 16px; border-top: 1px solid #dee2e6;">
							<a href="${docUrl}" target="_blank" style="
								color: #2196F3;
								text-decoration: none;
								font-size: 14px;
								font-weight: 600;
								display: inline-flex;
								align-items: center;
								gap: 6px;
								transition: color 0.2s;
							" onmouseover="this.style.color='#1976D2'" onmouseout="this.style.color='#2196F3'">
								View ${escapeHtml(doctypeName)} →
							</a>
						</div>
					`;
				}
				
				message += '</div>';
			}
		}
		
		// Handle count-only responses (e.g., from count_documents API)
		if (data && (data.total_count !== undefined || data.count !== undefined)) {
			const count = data.total_count || data.count || 0;
			
			// Determine the correct DocType to display
			let doctypeLabel = 'items';
			if (data.doctype) {
				// Use doctype from data (most accurate)
				doctypeLabel = data.doctype.toLowerCase();
			} else if (detected_doctypes && detected_doctypes.length > 0) {
				// Fallback to detected doctypes
				doctypeLabel = detected_doctypes[0].toLowerCase();
			} else if (ai_reasoning) {
				// Try to extract from AI reasoning
				const reasoningLower = ai_reasoning.toLowerCase();
				if (reasoningLower.includes('payment entry')) {
					doctypeLabel = 'payment entries';
				} else if (reasoningLower.includes('sales invoice')) {
					doctypeLabel = 'sales invoices';
				} else if (reasoningLower.includes('customer')) {
					doctypeLabel = 'customers';
				}
			}
			
			message += `<p style="font-size: 15px; font-weight: 600; color: #1f2937; margin-bottom: 12px;">
				You have <strong style="color: #4CAF50;">${count}</strong> ${doctypeLabel}.
			</p>`;
			
			// If there are results to show, display them
			if (data.results && Array.isArray(data.results) && data.results.length > 0) {
				message += '<div style="display: flex; flex-direction: column; gap: 12px; margin-top: 12px;">';
				data.results.slice(0, 10).forEach((item, index) => {
					message += `
						<div style="
							padding: 16px;
							background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
							border-radius: 12px;
							border-left: 4px solid #4CAF50;
							box-shadow: 0 2px 6px rgba(0,0,0,0.05);
							transition: transform 0.2s, box-shadow 0.2s;
						" onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 4px 12px rgba(0,0,0,0.1)';" onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 2px 6px rgba(0,0,0,0.05)';">
					`;
					
					const fields = Object.entries(item);
					fields.forEach(([key, value], idx) => {
						const isFirstField = idx === 0;
						const style = isFirstField 
							? 'font-size: 16px; font-weight: 700; color: #1f2937; margin-bottom: 8px;'
							: 'font-size: 14px; color: #4b5563; margin-bottom: 6px;';
						const label = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
						
						message += `
							<div style="${style}">
								${isFirstField 
									? `<span style="color: #4CAF50;">●</span> ${escapeHtml(String(value))}`
									: `<span style="color: #9ca3af; font-weight: 600;">${escapeHtml(label)}:</span> <span style="font-weight: 500;">${escapeHtml(String(value))}</span>`
								}
							</div>
						`;
					});
					
					if (item.name && detected_doctypes && detected_doctypes.length > 0) {
						const doctype = detected_doctypes[0];
						const docUrl = `/app/${doctype.toLowerCase().replace(/ /g, '-')}/${item.name}`;
						message += `
							<div style="margin-top: 12px;">
								<a href="${docUrl}" target="_blank" style="
									color: #2196F3;
									text-decoration: none;
									font-size: 13px;
									font-weight: 600;
									display: inline-flex;
									align-items: center;
									gap: 4px;
									transition: color 0.2s;
								" onmouseover="this.style.color='#1976D2'" onmouseout="this.style.color='#2196F3'">
									View ${doctype} →
								</a>
							</div>
						`;
					}
					
					message += '</div>';
				});
				message += '</div>';
			}
		} else if (data && data.results) {
			const results = Array.isArray(data.results) ? data.results : [data.results];
			const count = data.count || results.length;

			// Check if this is a single aggregation result (like SUM, COUNT)
			const isAggregationResult = count === 1 && results.length === 1 && 
										Object.keys(results[0]).length <= 3 &&
										(Object.keys(results[0]).some(k => k.toLowerCase().includes('sum') || 
																		  k.toLowerCase().includes('count') ||
																		  k.toLowerCase().includes('total') ||
																		  k.toLowerCase().includes('avg')));

			if (isAggregationResult) {
				// Display aggregation result as a simple answer
				const result = results[0];
				const keys = Object.keys(result);
				const values = Object.values(result);
				
				message += `<div style="padding: 20px; background: linear-gradient(135deg, #e0f2fe 0%, #bae6fd 100%); border-radius: 12px; border-left: 4px solid #0ea5e9; margin-top: 12px;">`;
				
				keys.forEach((key, idx) => {
					const value = values[idx];
					const label = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
					const isNumeric = typeof value === 'number' || (typeof value === 'string' && !isNaN(parseFloat(value)));
					
					message += `
						<div style="margin-bottom: ${idx < keys.length - 1 ? '12px' : '0'};">
							<div style="font-size: 13px; color: #0369a1; font-weight: 600; margin-bottom: 4px;">
								${escapeHtml(label)}:
							</div>
							<div style="font-size: 24px; font-weight: 700; color: #0c4a6e;">
								${isNumeric && typeof value === 'number' ? value.toLocaleString() : escapeHtml(String(value))}
							</div>
						</div>
					`;
				});
				
				message += `</div>`;
			} else {
				// Display as list of results
				message += `<p style="font-size: 15px; font-weight: 600; color: #1f2937; margin-bottom: 12px;">
					I found <strong style="color: #4CAF50;">${count}</strong> ${count === 1 ? 'result' : 'results'}:
				</p>`;

				message += '<div style="display: flex; flex-direction: column; gap: 12px; margin-top: 12px;">';

				// Display up to 10 results
				results.slice(0, 10).forEach((item, index) => {
				message += `
					<div style="
						padding: 16px;
						background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
						border-radius: 12px;
						border-left: 4px solid #4CAF50;
						box-shadow: 0 2px 6px rgba(0,0,0,0.05);
						transition: transform 0.2s, box-shadow 0.2s;
					" onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 4px 12px rgba(0,0,0,0.1)';" onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 2px 6px rgba(0,0,0,0.05)';">
				`;

				// Display all fields
				const fields = Object.entries(item);
				fields.forEach(([key, value], idx) => {
					const isFirstField = idx === 0;
					const style = isFirstField 
						? 'font-size: 16px; font-weight: 700; color: #1f2937; margin-bottom: 8px;'
						: 'font-size: 14px; color: #4b5563; margin-bottom: 6px;';

					const label = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
					
					message += `
						<div style="${style}">
							${isFirstField 
								? `<span style="color: #4CAF50;">●</span> ${escapeHtml(String(value))}`
								: `<span style="color: #9ca3af; font-weight: 600;">${escapeHtml(label)}:</span> <span style="font-weight: 500;">${escapeHtml(String(value))}</span>`
							}
						</div>
					`;
				});

				// Add "View" link if there's a "name" field (ERPNext document)
				if (item.name && detected_doctypes && detected_doctypes.length > 0) {
					const doctype = detected_doctypes[0];
					const docUrl = `/app/${doctype.toLowerCase().replace(/ /g, '-')}/${item.name}`;
					message += `
						<div style="margin-top: 12px;">
							<a href="${docUrl}" target="_blank" style="
								color: #2196F3;
								text-decoration: none;
								font-size: 13px;
								font-weight: 600;
								display: inline-flex;
								align-items: center;
								gap: 4px;
								transition: color 0.2s;
							" onmouseover="this.style.color='#1976D2'" onmouseout="this.style.color='#2196F3'">
								View ${doctype} →
							</a>
						</div>
					`;
				}

				message += '</div>';
			});

				message += '</div>';

				// Show "and X more" if there are more results
				if (results.length > 10) {
					message += `
						<p style="margin-top: 16px; font-size: 13px; color: #6b7280; font-style: italic;">
							...and ${results.length - 10} more result${results.length - 10 === 1 ? '' : 's'}
						</p>
					`;
				}
			}

			// Show query executed for dynamic queries
			if (data.query_executed) {
				message += `
					<details style="margin-top: 16px; padding: 12px; background: #f3f4f6; border-radius: 8px;">
						<summary style="cursor: pointer; font-weight: 600; color: #4b5563; font-size: 13px;">
							🔍 Query Details
						</summary>
						<pre style="
							margin-top: 8px;
							padding: 12px;
							background: #1f2937;
							color: #10b981;
							border-radius: 6px;
							font-size: 12px;
							overflow-x: auto;
							font-family: 'Courier New', monospace;
						">${escapeHtml(data.query_executed)}</pre>
					</details>
				`;
			}
		} else if (!data || (!data.total_count && !data.count && !data.results)) {
			// Only show "no results" if we truly have no data
			message += `
				<div style="padding: 20px; background: #fef3c7; border-radius: 8px; border-left: 3px solid #f59e0b;">
					<p style="font-size: 14px; color: #92400e; margin: 0;">
						⚠️ No results found for your query.
					</p>
				</div>
			`;
		}

		// Show Execution Type Badge
		const executionBadge = execution_type === 'direct_api'
			? `<span style="
				background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
				color: white;
				padding: 6px 14px;
				border-radius: 16px;
				font-size: 12px;
				font-weight: 700;
				display: inline-flex;
				align-items: center;
				gap: 6px;
				box-shadow: 0 2px 6px rgba(76, 175, 80, 0.3);
			">
				⚡ Direct API
			</span>`
			: `<span style="
				background: linear-gradient(135deg, #2196F3 0%, #1976D2 100%);
				color: white;
				padding: 6px 14px;
				border-radius: 16px;
				font-size: 12px;
				font-weight: 700;
				display: inline-flex;
				align-items: center;
				gap: 6px;
				box-shadow: 0 2px 6px rgba(33, 150, 243, 0.3);
			">
				🧠 Dynamic Query
			</span>`;

		message += `
			<div style="margin-top: 20px; display: flex; justify-content: space-between; align-items: center; padding-top: 16px; border-top: 1px solid #e5e7eb;">
				<div>${executionBadge}</div>
				<div style="font-size: 11px; color: #9ca3af;">
					Powered by Intelligent Query System
				</div>
			</div>
		`;

		message += '</div>';

		addMessage('ai', message);
	};
	*/

	// ============================================================================
	// END OF INTELLIGENT QUERY SYSTEM - DISABLED (COMMENTED OUT)
	// ============================================================================

	// Initialize when DOM is ready
	if (document.readyState === 'loading') {
		document.addEventListener('DOMContentLoaded', init);
	} else {
		init();
	}
})();

