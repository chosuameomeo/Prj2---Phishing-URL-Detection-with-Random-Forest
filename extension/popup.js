document.addEventListener('DOMContentLoaded', function () {
    // Lấy các phần tử HTML từ trang
    const urlDisplayElement = document.getElementById('original-url');
    const goBackButton = document.getElementById('go-back');
    const proceedButton = document.getElementById('proceed-anyway');

    // Lấy URL bị chặn từ tham số trên thanh địa chỉ
    const urlParams = new URLSearchParams(window.location.search);
    const blockedUrl = urlParams.get('url');

    // Hiển thị URL bị chặn lên màn hình
    // Kiểm tra xem blockedUrl có tồn tại không
    if (blockedUrl) {
        // Nếu có, hiển thị nó trong div 'original-url'
        urlDisplayElement.textContent = blockedUrl;
    } else {
        // Nếu không tìm thấy, hiển thị thông báo lỗi
        urlDisplayElement.textContent = 'Lỗi: Không thể xác định được URL.';
    }

    goBackButton.addEventListener('click', function () {
        window.location.href = 'https://www.google.com';
    });

    proceedButton.addEventListener('click', function () {
        if (blockedUrl) {
            chrome.runtime.sendMessage({
                action: 'proceedToUrl',
                url: blockedUrl
            });
        }
    });
});