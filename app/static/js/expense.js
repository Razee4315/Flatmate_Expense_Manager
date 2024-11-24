// Expense splitting functionality

document.addEventListener('DOMContentLoaded', function() {
    // Get DOM elements
    const expenseForm = document.getElementById('expenseForm');
    const amountInput = document.getElementById('amount');
    const isSharedCheckbox = document.getElementById('is_shared');
    const splitDetails = document.getElementById('split_details');
    const splitTypeEqual = document.getElementById('split_equal');
    const splitTypeCustom = document.getElementById('split_custom');
    const equalSplitDiv = document.getElementById('equal_split');
    const customSplitDiv = document.getElementById('custom_split');
    const memberCheckboxes = document.querySelectorAll('.member-checkbox');
    const customShareInputs = document.querySelectorAll('.custom-share');
    
    // Preview elements
    const previewAmount = document.getElementById('preview_amount');
    const previewCategory = document.getElementById('preview_category');
    const previewSplitType = document.getElementById('preview_split_type');
    const previewYourShare = document.getElementById('preview_your_share');
    const previewMembers = document.getElementById('preview_members');

    // Toggle split details visibility
    function toggleSplitDetails() {
        splitDetails.style.display = isSharedCheckbox.checked ? 'block' : 'none';
        updatePreview();
    }

    // Toggle between equal and custom split
    function toggleSplitType() {
        if (splitTypeEqual.checked) {
            equalSplitDiv.classList.remove('d-none');
            customSplitDiv.classList.add('d-none');
            customShareInputs.forEach(input => input.disabled = true);
            memberCheckboxes.forEach(cb => cb.disabled = false);
        } else {
            equalSplitDiv.classList.add('d-none');
            customSplitDiv.classList.remove('d-none');
            customShareInputs.forEach(input => input.disabled = false);
            memberCheckboxes.forEach(cb => cb.disabled = true);
        }
        updatePreview();
    }

    // Calculate shares
    function calculateShares() {
        const amount = parseFloat(amountInput.value) || 0;
        let yourShare = 0;
        let splitWith = [];

        if (!isSharedCheckbox.checked) {
            yourShare = amount;
        } else if (splitTypeEqual.checked) {
            const checkedMembers = Array.from(memberCheckboxes).filter(cb => cb.checked);
            const totalMembers = checkedMembers.length + 1; // +1 for current user
            yourShare = amount / totalMembers;
            splitWith = checkedMembers.map(cb => cb.dataset.name);
        } else {
            let totalCustomShares = 0;
            customShareInputs.forEach(input => {
                if (!input.disabled && input.value) {
                    const shareAmount = parseFloat(input.value) || 0;
                    totalCustomShares += shareAmount;
                    if (shareAmount > 0) {
                        const name = input.id.replace('custom_share_', '');
                        splitWith.push(document.querySelector(`label[for="member_${name}"]`).textContent.trim());
                    }
                }
            });
            yourShare = amount - totalCustomShares;
        }

        return {
            yourShare: yourShare,
            splitWith: splitWith
        };
    }

    // Update preview
    function updatePreview() {
        const amount = parseFloat(amountInput.value) || 0;
        const category = document.getElementById('category').value || '-';
        const shares = calculateShares();

        previewAmount.textContent = `$${amount.toFixed(2)}`;
        previewCategory.textContent = category;
        previewSplitType.textContent = !isSharedCheckbox.checked ? 'Not Split' :
                                     splitTypeEqual.checked ? 'Equal Split' : 'Custom Split';
        previewYourShare.textContent = `$${shares.yourShare.toFixed(2)}`;
        previewMembers.textContent = shares.splitWith.length ? shares.splitWith.join(', ') : '-';

        // Update custom split inputs
        if (splitTypeCustom.checked) {
            let remainingAmount = amount;
            customShareInputs.forEach(input => {
                if (!input.disabled && !input.value) {
                    input.placeholder = (remainingAmount / (customShareInputs.length + 1)).toFixed(2);
                } else if (!input.disabled) {
                    remainingAmount -= parseFloat(input.value) || 0;
                }
            });
        }
    }

    // Validate custom split total
    function validateCustomSplit() {
        if (!splitTypeCustom.checked) return true;

        const amount = parseFloat(amountInput.value) || 0;
        let totalCustomShares = 0;
        customShareInputs.forEach(input => {
            if (!input.disabled) {
                totalCustomShares += parseFloat(input.value) || 0;
            }
        });

        return Math.abs(totalCustomShares - amount) <= 0.01;
    }

    // Event listeners
    isSharedCheckbox.addEventListener('change', toggleSplitDetails);
    splitTypeEqual.addEventListener('change', toggleSplitType);
    splitTypeCustom.addEventListener('change', toggleSplitType);
    amountInput.addEventListener('input', updatePreview);
    memberCheckboxes.forEach(cb => cb.addEventListener('change', updatePreview));
    customShareInputs.forEach(input => input.addEventListener('input', updatePreview));

    // Form submission validation
    expenseForm.addEventListener('submit', function(event) {
        if (!validateCustomSplit()) {
            event.preventDefault();
            alert('The sum of custom shares must equal the total amount.');
            return;
        }

        if (isSharedCheckbox.checked && splitTypeEqual.checked) {
            const checkedMembers = Array.from(memberCheckboxes).filter(cb => cb.checked);
            if (checkedMembers.length === 0) {
                event.preventDefault();
                alert('Please select at least one member to split the expense with.');
                return;
            }
        }
    });

    // Initialize
    toggleSplitDetails();
    toggleSplitType();
    updatePreview();
});
