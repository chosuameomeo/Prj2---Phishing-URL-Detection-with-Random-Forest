chrome.tabs.onUpdated.addListener(async (tabId, changeInfo, tab) => {
  if (changeInfo.status === 'loading' && tab.url && tab.url.startsWith('http')) {
    
    const currentUrl = changeInfo.url;
    console.log(`Tab is loading a new URL: ${currentUrl}`);

    try {
      const currentHostname = new URL(currentUrl).hostname;

      const data = await chrome.storage.session.get(['allowedHostnames']);
      const allowedHostnames = data.allowedHostnames || [];

      if (allowedHostnames.includes(currentHostname)) {
        console.log(`Hostname ${currentHostname} is whitelisted. Allowing access to ${currentUrl}`);
        return; // Dừng xử lý 
      }

      // Gửi URL đến backend Python để kiểm tra
      const response = await fetch('http://127.0.0.1:5000/check_url', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ url: currentUrl })
      });

      // Nếu backend không phản hồi thành công, ghi log lỗi và không làm gì cả
      if (!response.ok) {
        console.error('Backend server returned an error:', response.status, response.statusText);
        return;
      }

      const result = await response.json();
      console.log(`Check result for ${currentUrl}:`, result);

      if (result.status === 'phishing') {
        console.log(`Phishing detected! Redirecting tab ${tabId}...`);

        // Tạo đường dẫn đến trang cảnh báo
        const warningPageUrl = chrome.runtime.getURL('popup.html') + '?url=' + encodeURIComponent(currentUrl);

        // **Hành động chính:** Cập nhật URL của tab hiện tại để chuyển hướng đến trang cảnh báo
        chrome.tabs.update(tabId, { url: warningPageUrl });
      }

    } catch (error) {
      console.error('Error connecting to the backend server:', error);
    }
  }
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  // Kiểm tra xem có đúng là hành động cho phép truy cập không
  if (message.action === 'proceedToUrl') {
    const urlToAllow = message.url;
    if (urlToAllow) {
      // Dùng hàm async để xử lý bất đồng bộ
      (async () => {
        const hostnameToAllow = new URL(urlToAllow).hostname;

        // Lấy danh sách trắng hiện tại
        const data = await chrome.storage.session.get(['allowedHostnames']);
        const allowedHostnames = data.allowedHostnames || [];

        // Thêm TÊN MIỀN mới vào danh sách nếu nó chưa có
        if (!allowedHostnames.includes(hostnameToAllow)) {
          allowedHostnames.push(hostnameToAllow);
        }

        // Lưu lại danh sách TÊN MIỀN đã cập nhật
        await chrome.storage.session.set({ allowedHostnames: allowedHostnames });
        console.log(`Whitelisted hostname: ${hostnameToAllow}. Now proceeding to original URL.`);
        
        // Chuyển hướng tab đã mở trang cảnh báo đến URL người dùng muốn
        const tabId = sender.tab.id;
        chrome.tabs.update(tabId, { url: urlToAllow });
      })();
    }
    // Trả về true để chỉ ra rằng chúng ta sẽ phản hồi một cách bất đồng bộ
    return true; 
  }
});

console.log("Phishing Detector service worker started.");