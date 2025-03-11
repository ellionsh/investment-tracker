document.addEventListener('DOMContentLoaded', () => {
    fetchAccounts();
    fetchMonthlyMarketValues();
    fetchTypeMarketValues();

    document.getElementById('accountType').addEventListener('change', handleTypeChange);
    document.getElementById('transferButton').addEventListener('click', showTransferModal);
    document.getElementById('submitTransferButton').addEventListener('click', transferFunds);
    document.getElementById('cancelTransferButton').addEventListener('click', hideTransferModal);
});

let editAccountId = null;

function handleTypeChange() {
    const type = document.getElementById('accountType').value;
    if (type === '股票账户') {
        document.getElementById('stockSymbol').style.display = '';
        document.getElementById('shares').style.display = '';
        document.getElementById('marketValue').style.display = 'none';
    } else {
        document.getElementById('stockSymbol').style.display = 'none';
        document.getElementById('shares').style.display = 'none';
        document.getElementById('marketValue').style.display = '';
    }
}

function fetchAccounts() {
    fetch('/api/accounts')
        .then(response => response.json())
        .then(data => {
            // 对数据按市值从大到小排序
            data.sort((a, b) => (b.marketValue || 0) - (a.marketValue || 0));

            const accountList = document.getElementById('accountList');
            const fromAccountSelect = document.getElementById('fromAccount');
            const toAccountSelect = document.getElementById('toAccount');
            accountList.innerHTML = '';
            fromAccountSelect.innerHTML = '<option value="">选择转出账户</option>';
            toAccountSelect.innerHTML = '<option value="">选择转入账户</option>';
            let totalMarketValue = 0;
            data.forEach(account => {
                totalMarketValue += account.marketValue || 0;
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${account.type}</td>
                    <td>${account.details}</td>
                    <td>${account.stockSymbol || ''}</td>
                    <td>${account.shares || ''}</td>
                    <td>${account.marketValue != null ? account.marketValue.toFixed(2) : 'N/A'}</td>
                    <td>
                        <button onclick="editAccount(${account.id})">编辑</button>
                        <button onclick="deleteAccount(${account.id})">删除</button>
                    </td>
                `;
                accountList.appendChild(row);

                const option = document.createElement('option');
                option.value = account.id;
                option.textContent = `${account.details} (${account.type})`;
                fromAccountSelect.appendChild(option);
                toAccountSelect.appendChild(option.cloneNode(true));
            });
            document.getElementById('totalMarketValue').textContent = totalMarketValue.toFixed(2);
        })
        .catch(error => console.error('Error fetching accounts:', error));
}

function fetchTypeMarketValues() {
    fetch('/api/typeMarketValues')
        .then(response => response.json())
        .then(data => {
            const typeMarketValues = document.getElementById('typeMarketValues');
            typeMarketValues.innerHTML = '';
            for (const [type, marketValue] of Object.entries(data)) {
                const row = document.createElement('tr');
                row.innerHTML = `<td>${type}</td><td>${marketValue.toFixed(2)}</td>`;
                typeMarketValues.appendChild(row);
            }
        })
        .catch(error => console.error('Error fetching type market values:', error));
}

function addAccount() {
    const type = document.getElementById('accountType').value;
    const details = document.getElementById('accountDetails').value;
    const stockSymbol = document.getElementById('stockSymbol').value;
    const shares = parseInt(document.getElementById('shares').value) || 0;
    const marketValue = parseFloat(document.getElementById('marketValue').value) || 0;

    const account = { type, details, stockSymbol, shares, marketValue };

    if (editAccountId) {
        fetch(`/api/accounts/${editAccountId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(account)
        })
            .then(response => response.json())
            .then(data => {
                fetchAccounts();
                fetchTypeMarketValues();
                clearForm();
                editAccountId = null;
                document.getElementById('addAccountButton').textContent = '添加账户';
            })
            .catch(error => console.error('Error updating account:', error));
    } else {
        fetch('/api/accounts', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(account)
        })
            .then(response => response.json())
            .then(data => {
                fetchAccounts();
                fetchTypeMarketValues();
                clearForm();
            })
            .catch(error => console.error('Error adding account:', error));
    }
}

function editAccount(id) {
    fetch(`/api/accounts/${id}`)
        .then(response => response.json())
        .then(account => {
            document.getElementById('accountType').value = account.type;
            document.getElementById('accountDetails').value = account.details;
            document.getElementById('stockSymbol').value = account.stockSymbol || '';
            document.getElementById('shares').value = account.shares || '';
            document.getElementById('marketValue').value = account.marketValue || 0;
            handleTypeChange();
            editAccountId = id;
            document.getElementById('addAccountButton').textContent = '更新账户';
        })
        .catch(error => console.error('Error fetching account:', error));
}

function deleteAccount(id) {
    fetch(`/api/accounts/${id}`, {
        method: 'DELETE'
    })
        .then(response => response.json())
        .then(data => {
            fetchAccounts();
            fetchTypeMarketValues();
        })
        .catch(error => console.error('Error deleting account:', error));
}

function refreshMarketValues() {
    fetch('/api/refresh', {
        method: 'POST'
    })
        .then(response => response.json())
        .then(data => {
            fetchAccounts();
            fetchTypeMarketValues();
        })
        .catch(error => console.error('Error refreshing market values:', error));
}

function fetchMonthlyMarketValues() {
    fetch('/api/monthlyMarketValues')
        .then(response => response.json())
        .then(data => {
            const ctx = document.getElementById('marketValueChart').getContext('2d');
            const chartData = {
                labels: data.map(value => new Date(value.month).toLocaleDateString()),
                datasets: [{
                    label: '总市值',
                    data: data.map(value => value.totalMarketValue),
                    borderColor: 'rgba(75,192,192,1)',
                    backgroundColor: 'rgba(75,192,192,0.2)',
                }]
            };
            const chartOptions = {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'top',
                    },
                    title: {
                        display: true,
                        text: '每个月的总市值变化',
                    },
                },
            };
            new Chart(ctx, {
                type: 'line',
                data: chartData,
                options: chartOptions
            });
        })
        .catch(error => console.error('Error fetching monthly market values:', error));
}

function clearForm() {
    document.getElementById('accountType').value = '银行账户';
    document.getElementById('accountDetails').value = '';
    document.getElementById('stockSymbol').value = '';
    document.getElementById('shares').value = '';
    document.getElementById('marketValue').value = '';
    handleTypeChange();
}

function showTransferModal() {
    document.getElementById('transferModal').style.display = 'block';
}

function hideTransferModal() {
    document.getElementById('transferModal').style.display = 'none';
}

function transferFunds() {
    const fromAccountId = parseInt(document.getElementById('fromAccount').value);
    const toAccountId = parseInt(document.getElementById('toAccount').value);
    const amount = parseFloat(document.getElementById('transferAmount').value);

    if (isNaN(fromAccountId) || isNaN(toAccountId) || isNaN(amount) || amount <= 0) {
        alert('请输入有效的转账信息');
        return;
    }

    fetch('/api/transfer', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            fromAccountId,
            toAccountId,
            amount
        })
    })
    .then(response => response.json())
    .then(data => {
        hideTransferModal();
        fetchAccounts();
        fetchTypeMarketValues();
        if (data.message) {
            alert(data.message);
        } else {
            alert('转账成功');
        }
    })
    .catch(error => console.error('Error transferring funds:', error));
}
