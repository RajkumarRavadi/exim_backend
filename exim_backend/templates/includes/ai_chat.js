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
	let currentFile = null; // For PDFs
	let currentFileType = null; // 'image' or 'pdf'
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

	// Handle file upload (image or PDF)
	const handleImageUpload = (e) => {
		const file = e.target.files[0];
		if (!file) return;

		// Check if it's a PDF
		if (file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf')) {
			// Handle PDF
			currentFile = file;
			currentFileType = 'pdf';
			currentImage = null;
			
			// Show PDF preview
			previewImg.style.display = 'none';
			imagePreview.classList.add('active');
			imagePreview.innerHTML = `
				<div style="display: flex; align-items: center; justify-content: center; height: 100%; background: #f0f4f8; flex-direction: column; gap: 5px;">
					<div style="font-size: 32px;">📄</div>
					<div style="font-size: 11px; text-align: center; padding: 0 5px; word-break: break-all;">${file.name}</div>
				</div>
				<button class="image-preview-remove" id="removeImage" style="position: absolute; top: 5px; right: 5px; background: rgba(0,0,0,0.6); color: white; border: none; border-radius: 50%; width: 24px; height: 24px; cursor: pointer; display: flex; align-items: center; justify-content: center; font-size: 14px;">×</button>
			`;
			
			// Re-attach remove event
			const newRemoveBtn = document.getElementById('removeImage');
			if (newRemoveBtn) {
				newRemoveBtn.addEventListener('click', handleRemoveImage);
			}
			
			return;
		}

		// Validate image file type
		if (!file.type.startsWith('image/')) {
			showError('Please upload a valid image or PDF file');
			return;
		}

		// Handle image
		currentFileType = 'image';
		currentImage = file;
		currentFile = null;
		
		// Preview image
		const reader = new FileReader();
		reader.onload = (event) => {
			previewImg.src = event.target.result;
			previewImg.style.display = 'block';
			imagePreview.classList.add('active');
			imagePreview.innerHTML = `
				<img src="${event.target.result}" alt="Preview" id="previewImg" style="width: 100%; height: 100%; object-fit: cover;">
				<button class="image-preview-remove" id="removeImage" style="position: absolute; top: 5px; right: 5px; background: rgba(0,0,0,0.6); color: white; border: none; border-radius: 50%; width: 24px; height: 24px; cursor: pointer; display: flex; align-items: center; justify-content: center; font-size: 14px;">×</button>
			`;
			
			// Re-attach remove event
			const newRemoveBtn = document.getElementById('removeImage');
			if (newRemoveBtn) {
				newRemoveBtn.addEventListener('click', handleRemoveImage);
			}
		};
		reader.readAsDataURL(file);
	};

	// Handle remove image/PDF
	const handleRemoveImage = () => {
		imagePreview.classList.remove('active');
		previewImg.src = '';
		currentImage = null;
		currentFile = null;
		currentFileType = null;
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
						<p>Send a message, upload an image, or upload a PDF sales order</p>
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
		if (!message && !currentImage && !currentFile) {
			showError('Please enter a message, upload an image, or upload a PDF');
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

		if (currentFile) {
			// Add PDF message
			const pdfMessage = message ? `${message}\n\n📄 Analyzing: ${currentFile.name}` : `📄 Analyzing PDF for sales order: ${currentFile.name}`;
			// Override the user message to include PDF info
			if (!message) {
				addMessage(pdfMessage, 'user');
			}
		}

		// Clear input
		const messageToSend = message;
		const imageToSend = currentImage;
		const fileToSend = currentFile;
		const fileTypeToSend = currentFileType;
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
			const response = await sendChatMessage(messageToSend, imageToSend, fileToSend, fileTypeToSend);
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

			// Handle PDF sales order response (requires_action = true)
			if (response.status === 'success' && response.requires_action && response.response) {
				console.log('PDF Sales Order Response detected');
				const formattedMessage = formatPDFResponse(response.response);
				addMessage(formattedMessage, 'ai', null, null);
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
							addMessage(markdownToHtml(messageText), 'ai', null, response.token_usage);
						} else {
							// Plain text - wrap in paragraph
							addMessage(`<p class="ai-paragraph">${escapeHtml(messageText)}</p>`, 'ai', null, response.token_usage);
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
						addMessage(markdownToHtml(messageText), 'ai', response.suggested_action, response.token_usage);
					} else {
						// Plain text - wrap in paragraph
						addMessage(`<p class="ai-paragraph">${escapeHtml(messageText)}</p>`, 'ai', response.suggested_action, response.token_usage);
					}
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
		
		// Close any unclosed divs
		html += '</div></div>';
		
		return html;
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
			// For AI messages, content should already be HTML (converted from markdown)
			// Just render it directly
			if (content && typeof content === 'string') {
				messageContent.innerHTML = content;
			} else {
				messageContent.innerHTML = content || '';
			}
			
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

		addMessage(message, 'ai');
	};

	// Handle dynamic search with filters
	const handleDynamicSearch = async (action) => {
		try {
			showTypingIndicator();
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

		addMessage(message, 'ai');
	};

	// Handle get customers by order count
	const handleGetCustomersByOrderCount = async (action) => {
		try {
			showTypingIndicator();
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
			hideTypingIndicator();

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
				addMessage(message, 'ai');
			} else {
				addMessage(`❌ ${result.message || 'Failed to get customers by order count'}`, 'ai');
			}
		} catch (error) {
			hideTypingIndicator();
			addMessage('❌ Error fetching customers by order count. Please try again.', 'ai');
			console.error('Get customers by order count error:', error);
		}
	};

	// Handle get customers by order value
	const handleGetCustomersByOrderValue = async (action) => {
		try {
			showTypingIndicator();
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
			hideTypingIndicator();

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
				addMessage(message, 'ai');
			} else {
				addMessage(`❌ ${result.message || 'Failed to get customers by order value'}`, 'ai');
			}
		} catch (error) {
			hideTypingIndicator();
			addMessage('❌ Error fetching customers by order value. Please try again.', 'ai');
			console.error('Get customers by order value error:', error);
		}
	};

	// Handle get orders by customer group
	const handleGetOrdersByCustomerGroup = async (action) => {
		try {
			showTypingIndicator();
			const customer_group = action?.customer_group;
			
			if (!customer_group) {
				hideTypingIndicator();
				addMessage('❌ Customer group is required', 'ai');
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
			hideTypingIndicator();

			if (result.status === 'success') {
				// Use the same display function as dynamic search
				displayDynamicSearchResults(result, 'Sales Order');
			} else {
				addMessage(`❌ ${result.message || 'Failed to get orders by customer group'}`, 'ai');
			}
		} catch (error) {
			hideTypingIndicator();
			addMessage('❌ Error fetching orders by customer group. Please try again.', 'ai');
			console.error('Get orders by customer group error:', error);
		}
	};

	// Handle get orders by territory
	const handleGetOrdersByTerritory = async (action) => {
		try {
			showTypingIndicator();
			const territory = action?.territory;
			
			if (!territory) {
				hideTypingIndicator();
				addMessage('❌ Territory is required', 'ai');
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
			hideTypingIndicator();

			if (result.status === 'success') {
				// Use the same display function as dynamic search
				displayDynamicSearchResults(result, 'Sales Order');
			} else {
				addMessage(`❌ ${result.message || 'Failed to get orders by territory'}`, 'ai');
			}
		} catch (error) {
			hideTypingIndicator();
			addMessage('❌ Error fetching orders by territory. Please try again.', 'ai');
			console.error('Get orders by territory error:', error);
		}
	};

	// Handle get orders by item
	const handleGetOrdersByItem = async (action) => {
		try {
			showTypingIndicator();
			const item_code = action?.item_code;
			
			if (!item_code) {
				hideTypingIndicator();
				addMessage('❌ Item code is required', 'ai');
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
			hideTypingIndicator();

			if (result.status === 'success') {
				// Use the same display function as dynamic search
				displayDynamicSearchResults(result, 'Sales Order');
			} else {
				addMessage(`❌ ${result.message || 'Failed to get orders by item'}`, 'ai');
			}
		} catch (error) {
			hideTypingIndicator();
			addMessage('❌ Error fetching orders by item. Please try again.', 'ai');
			console.error('Get orders by item error:', error);
		}
	};

	// Handle get orders with most items
	const handleGetOrdersWithMostItems = async (action) => {
		try {
			showTypingIndicator();
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
			hideTypingIndicator();

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
				addMessage(message, 'ai');
			} else {
				addMessage(`❌ ${result.message || 'Failed to get orders with most items'}`, 'ai');
			}
		} catch (error) {
			hideTypingIndicator();
			addMessage('❌ Error fetching orders with most items. Please try again.', 'ai');
			console.error('Get orders with most items error:', error);
		}
	};

	// Handle get orders by item group
	const handleGetOrdersByItemGroup = async (action) => {
		try {
			showTypingIndicator();
			const item_group = action?.item_group;
			
			if (!item_group) {
				hideTypingIndicator();
				addMessage('❌ Item group is required', 'ai');
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
			hideTypingIndicator();

			if (result.status === 'success') {
				// Use the same display function as dynamic search
				displayDynamicSearchResults(result, 'Sales Order');
			} else {
				addMessage(`❌ ${result.message || 'Failed to get orders by item group'}`, 'ai');
			}
		} catch (error) {
			hideTypingIndicator();
			addMessage('❌ Error fetching orders by item group. Please try again.', 'ai');
			console.error('Get orders by item group error:', error);
		}
	};

	// Handle get total quantity sold
	const handleGetTotalQuantitySold = async (action) => {
		try {
			showTypingIndicator();
			const item_code = action?.item_code;
			
			if (!item_code) {
				hideTypingIndicator();
				addMessage('❌ Item code is required', 'ai');
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
			hideTypingIndicator();

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
				addMessage(message, 'ai');
			} else {
				addMessage(`❌ ${result.message || 'Failed to get total quantity sold'}`, 'ai');
			}
		} catch (error) {
			hideTypingIndicator();
			addMessage('❌ Error fetching total quantity sold. Please try again.', 'ai');
			console.error('Get total quantity sold error:', error);
		}
	};

	// Handle get most sold items
	const handleGetMostSoldItems = async (action) => {
		try {
			showTypingIndicator();
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
			hideTypingIndicator();

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
				addMessage(message, 'ai');
			} else {
				addMessage(`❌ ${result.message || 'Failed to get most sold items'}`, 'ai');
			}
		} catch (error) {
			hideTypingIndicator();
			addMessage('❌ Error fetching most sold items. Please try again.', 'ai');
			console.error('Get most sold items error:', error);
		}
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
			
			hideTypingIndicator();
			
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
						addMessage(`<p class="ai-paragraph">${escapeHtml(cleanAnswer)}</p>`, 'ai', null, result.token_usage);
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
			console.log('🔍 Checking result.sales_order:', result?.sales_order);
			console.log('🔍 Type of result.sales_order:', typeof result?.sales_order);
			console.log('🔍 Has sales_order key:', 'sales_order' in (result || {}));
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

	// Display Sales Order details
	const displaySalesOrderDetails = (salesOrder) => {
		try {
			if (!salesOrder || typeof salesOrder !== 'object') {
				console.error('displaySalesOrderDetails: salesOrder is invalid', salesOrder);
				addMessage(`❌ Error: Sales Order data is missing or invalid.`, 'ai');
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

			addMessage(message, 'ai');
		} catch (error) {
			console.error('displaySalesOrderDetails error:', error, { salesOrder });
			addMessage(`❌ Error displaying Sales Order details: ${error.message || 'Unknown error'}`, 'ai');
		}
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

