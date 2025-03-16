document.addEventListener('DOMContentLoaded', () => {
    fetchAccounts();
    fetchMonthlyMarketValues();
    fetchTypeMarketValues();

    document.getElementById('accountType').addEventListener('change', handleTypeChange);
    document.getElementById('incomeButton').addEventListener('click', showIncomeModal);
    document.getElementById('expenseButton').addEventListener('click', showExpenseModal);
    document.getElementById('transactionsButton').addEventListener('click', showTransactionsModal);
    document.getElementById('transferButton').addEventListener('click', showTransferModal);
    document.getElementById('submitIncomeButton').addEventListener('click', addIncome);
    document.getElementById('submitExpenseButton').addEventListener('click', addExpense);
    document.getElementById('submitTransferButton').addEventListener('click', transferFunds);
    document.getElementById('submitTransactionsButton').addEventListener('click', fetchTransactions);
    document.getElementById('cancelIncomeButton').addEventListener('click', hideIncomeModal);
    document.getElementById('cancelExpenseButton').addEventListener('click', hideExpenseModal);
    document.getElementById('cancelTransactionsButton').addEventListener('click', hideTransactionsModal);
    document.getElementById('cancelTransferButton').addEventListener('click', hideTransferModal);
    document.getElementById('confirmDeleteButton').addEventListener('click', confirmDeleteAccount);
    document.getElementById('cancelDeleteButton').addEventListener('click', hideDeleteConfirmModal);

    // Set default date range to current month for transactions
    setDefaultDateRange();
});

let editAccountId = null;
let deleteAccountId = null;

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
            data.sort((a, b) => (parseFloat(b.marketValue) || 0) - (parseFloat(a.marketValue) || 0));

            const accountList = document.getElementById('accountList');
            const fromAccountSelect = document.getElementById('fromAccount');
            const toAccountSelect = document.getElementById('toAccount');
            const incomeAccountSelect = document.getElementById('incomeAccount');
            const expenseAccountSelect = document.getElementById('expenseAccount');
            accountList.innerHTML = '';
            fromAccountSelect.innerHTML = '<option value="">选择转出账户</option>';
            toAccountSelect.innerHTML = '<option value="">选择转入账户</option>';
            incomeAccountSelect.innerHTML = '<option value="">选择账户</option>';
            expenseAccountSelect.innerHTML = '<option value="">选择账户</option>';
            let totalMarketValue = 0;
            data.forEach(account => {
                totalMarketValue += parseFloat(account.marketValue) || 0;
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${account.type}</td>
                    <td>${account.details}</td>
                    <td>${account.stockSymbol || ''}</td>
                    <td>${account.shares || ''}</td>
                    <td>${account.marketValue != null ? account.marketValue : 'N/A'}</td>
                    <td>
                        <button onclick="editAccount(${account.id})">编辑</button>
                        <button onclick="showDeleteConfirmModal(${account.id})">删除</button>
                    </td>
                `;
                accountList.appendChild(row);

                const option = document.createElement('option');
                option.value = account.id;
                option.textContent = `${account.details} (${account.type})`;
                fromAccountSelect.appendChild(option);
                toAccountSelect.appendChild(option.cloneNode(true));
                incomeAccountSelect.appendChild(option.cloneNode(true));
                expenseAccountSelect.appendChild(option.cloneNode(true));
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
                row.innerHTML = `<td>${type}</td><td>${marketValue}</td>`;
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
                //alert('账户更新成功');
            })
            .catch(error => {
                console.error('Error updating account:', error);
                alert('账户更新失败');
            });
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
                //showInfoModal('账户添加成功');
            })
            .catch(error => {
                console.error('Error adding account:', error);
                alert('账户添加失败');
            });
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

function showDeleteConfirmModal(id) {
    deleteAccountId = id;
    document.getElementById('deleteConfirmModal').style.display = 'block';
}

function hideDeleteConfirmModal() {
    deleteAccountId = null;
    document.getElementById('deleteConfirmModal').style.display = 'none';
}

function confirmDeleteAccount() {
    if (deleteAccountId) {
        fetch(`/api/accounts/${deleteAccountId}`, {
            method: 'DELETE'
        })
            .then(response => response.json())
            .then(data => {
                fetchAccounts();
                fetchTypeMarketValues();
                hideDeleteConfirmModal();
                alert('账户删除成功');
            })
            .catch(error => {
                console.error('Error deleting account:', error);
                alert('账户删除失败');
            });
    }
}

function refreshMarketValues() {
    fetch('/api/refresh', {
        method: 'POST'
    })
        .then(response => response.json())
        .then(data => {
            fetchAccounts();
            fetchTypeMarketValues();
            alert('市值刷新成功');
        })
        .catch(error => {
            console.error('Error refreshing market values:', error);
            alert('市值刷新失败');
        });
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

function showIncomeModal() {
    document.getElementById('incomeModal').style.display = 'block';
}

function hideIncomeModal() {
    document.getElementById('incomeModal').style.display = 'none';
}

function showExpenseModal() {
    document.getElementById('expenseModal').style.display = 'block';
}

function hideExpenseModal() {
    document.getElementById('expenseModal').style.display = 'none';
}

function showTransactionsModal() {
    document.getElementById('transactionsModal').style.display = 'block';
}

function hideTransactionsModal() {
    document.getElementById('transactionsModal').style.display = 'none';
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
    .catch(error => {
        console.error('Error transferring funds:', error);
        alert('转账失败');
    });
}

function addIncome() {
    const accountId = parseInt(document.getElementById('incomeAccount').value);
    const reason = document.getElementById('incomeReason').value;
    const amount = parseFloat(document.getElementById('incomeAmount').value);

    if (isNaN(accountId) || isNaN(amount) || amount <= 0) {
        alert('请输入有效的收入信息');
        return;
    }

    fetch('/api/income', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            accountId,
            reason,
            amount
        })
    })
    .then(response => response.json())
    .then(data => {
        hideIncomeModal();
        fetchAccounts();
        fetchTypeMarketValues();
        if (data.message) {
            alert(data.message);
        } else {
            alert('收入已记录');
        }
    })
    .catch(error => {
        console.error('Error adding income:', error);
        alert('收入记录失败');
    });
}

function addExpense() {
    const accountId = parseInt(document.getElementById('expenseAccount').value);
    const reason = document.getElementById('expenseReason').value;
    const amount = parseFloat(document.getElementById('expenseAmount').value);

    if (isNaN(accountId) || isNaN(amount) || amount <= 0) {
        alert('请输入有效的支出信息');
        return;
    }

    fetch('/api/expense', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            accountId,
            reason,
            amount
        })
    })
    .then(response => response.json())
    .then(data => {
        hideExpenseModal();
        fetchAccounts();
        fetchTypeMarketValues();
        if (data.message) {
            alert(data.message);
        } else {
            alert('支出已记录');
        }
    })
    .catch(error => {
        console.error('Error adding expense:', error);
        alert('支出记录失败');
    });
}

function fetchTransactions() {
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;

    if (!startDate || !endDate || startDate > endDate) {
        alert('请输入有效的日期范围');
        return;
    }

    fetch(`/api/transactions?start=${startDate}&end=${endDate}`)
        .then(response => response.json())
        .then(data => {
            const transactionsList = document.getElementById('transactionsList');
            transactionsList.innerHTML = '';
            data.forEach(transaction => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${transaction.accountDetails || '已经删除账户'}</td>
                    <td>${transaction.change}</td>
                    <td>${transaction.reason}</td>
                    <td>${transaction.timestamp}</td>
                `;
                transactionsList.appendChild(row);
            });
        })
        .catch(error => {
            console.error('Error fetching transactions:', error);
            alert('获取流水记录失败');
        });
}

function setDefaultDateRange() {
    const startDate = document.getElementById('startDate');
    const endDate = document.getElementById('endDate');

    const now = new Date();
    const firstDayOfMonth = new Date(now.getFullYear(), now.getMonth(), 1);

    startDate.value = firstDayOfMonth.toISOString().split('T')[0];
    endDate.value = now.toISOString().split('T')[0];
}

function showInfoModal(message) {
    document.getElementById('infoModalBody').textContent = message;
    $('#infoModal').modal('show');
}
