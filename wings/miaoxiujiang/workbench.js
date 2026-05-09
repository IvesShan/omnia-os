// ===== 确认收货功能 =====
let currentDeliveryType = null;
let currentCustomerPhone = '';
let currentExpressCompany = '';
let currentExpressNumber = '';

function openReceiveModal(orderNo) {
    currentOrderNo = orderNo;
    const order = allOrders.find(o => o.order_no === orderNo);
    if (!order) return;
    
    currentDeliveryType = order.delivery_type || 'express';
    currentCustomerPhone = order.customer_phone || '';
    currentExpressCompany = order.express_company || '';
    currentExpressNumber = order.express_number || '';
    
    document.getElementById('receiveOrderNo').textContent = orderNo;
    
    const expressForm = document.getElementById('receiveExpressForm');
    const shopForm = document.getElementById('receiveShopForm');
    
    if (currentDeliveryType === 'express') {
        expressForm.style.display = 'block';
        shopForm.style.display = 'none';
        document.getElementById('customerExpressCompany').value = currentExpressCompany || '-';
        document.getElementById('customerExpressNumber').value = currentExpressNumber || '-';
        document.getElementById('receivedExpressNumber').value = '';
        document.getElementById('expressMismatchWarning').style.display = 'none';
    } else {
        expressForm.style.display = 'none';
        shopForm.style.display = 'block';
        document.getElementById('customerAppointmentTime').value = order.appointment_time 
            ? new Date(order.appointment_time).toLocaleString('zh-CN') 
            : '-';
        document.getElementById('verifyPhone').value = '';
        document.getElementById('phoneMismatchWarning').style.display = 'none';
    }
    
    document.getElementById('receiveModal').classList.add('active');
}

async function confirmReceive() {
    if (!currentOrderNo) return;
    
    if (currentDeliveryType === 'express') {
        const receivedNumber = document.getElementById('receivedExpressNumber').value.trim().toUpperCase();
        const customerNumber = currentExpressNumber.toUpperCase();
        
        if (!receivedNumber) {
            showToast('请输入收到的快递单号');
            return;
        }
        
        if (receivedNumber !== customerNumber) {
            document.getElementById('expressMismatchWarning').style.display = 'block';
            if (!confirm('快递单号不匹配！\n客户填写：' + customerNumber + '\n您收到：' + receivedNumber + '\n\n是否确认继续？')) {
                return;
            }
        }
        
        try {
            const res = await fetch(`${API_BASE}/order/receive`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    order_no: currentOrderNo,
                    received_express_number: receivedNumber
                })
            });
            
            const data = await res.json();
            if (data.success) {
                showToast('✅ 确认收货成功！');
                closeModals();
                loadOrders();
            } else {
                showToast('❌ ' + (data.message || '操作失败'));
            }
        } catch (e) {
            showToast('❌ 网络错误');
        }
    } else {
        const phoneSuffix = document.getElementById('verifyPhone').value.trim();
        const customerSuffix = currentCustomerPhone.slice(-4);
        
        if (!phoneSuffix) {
            showToast('请输入客户手机号后4位');
            return;
        }
        
        if (phoneSuffix !== customerSuffix) {
            document.getElementById('phoneMismatchWarning').style.display = 'block';
            return;
        }
        
        try {
            const res = await fetch(`${API_BASE}/order/receive`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    order_no: currentOrderNo,
                    verified_phone_suffix: phoneSuffix
                })
            });
            
            const data = await res.json();
            if (data.success) {
                showToast('✅ 客户已到店，开始检测！');
                closeModals();
                loadOrders();
            } else {
                showToast('❌ ' + (data.message || '操作失败'));
            }
        } catch (e) {
            showToast('❌ 网络错误');
        }
    }
}
