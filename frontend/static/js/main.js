$(document).ready(function() {
    $('[data-toggle="tooltip"]').tooltip();
    $('[data-toggle="popover"]').popover();
    
    const navbar = $('.navbar');
    $(window).scroll(function() {
        if($(window).scrollTop() > 50) {
            navbar.addClass('navbar-scroll');
        } else {
            navbar.removeClass('navbar-scroll');
        }
    });
    
    $('.quantity-up').click(function() {
        const input = $(this).closest('.quantity-selector').find('input');
        const max = parseInt(input.attr('max') || 99);
        let value = parseInt(input.val());
        
        if (value < max) {
            input.val(value + 1);
            
            input.trigger('change');
        }
    });
    
    $('.quantity-down').click(function() {
        const input = $(this).closest('.quantity-selector').find('input');
        let value = parseInt(input.val());
        
        if (value > 1) {
            input.val(value - 1);
            
            input.trigger('change');
        }
    });
    
    $('.quantity-input').change(function() {
        const productId = $(this).data('product-id');
        const quantity = parseInt($(this).val());
        
        if (productId && quantity >= 1) {
            updateCartItem(productId, quantity);
        }
    });
    
    $('.remove-item').click(function() {
        const productId = $(this).data('product-id');
        removeCartItem(productId);
    });
    
    function updateCartItem(productId, quantity) {
        $.ajax({
            url: '/cart/update',
            method: 'POST',
            data: {
                product_id: productId,
                quantity: quantity
            },
            success: function(response) {
                if (response.success) {
                    $(`.cart-item[data-product-id="${productId}"] .item-subtotal`).text(response.item_subtotal);
                    
                    $('#cart-subtotal').text(response.subtotal);
                    $('#cart-tax').text(response.tax);
                    $('#cart-total').text(response.total);
                    
                    $('.cart-count').text(response.item_count);
                }
            },
            error: function(xhr, status, error) {
                console.error('Error updating cart:', error);
                alert('There was an error updating your cart. Please try again.');
            }
        });
    }
    
    function removeCartItem(productId) {
        if (confirm('Are you sure you want to remove this item from your cart?')) {
            $.ajax({
                url: '/cart/remove',
                method: 'POST',
                data: {
                    product_id: productId
                },
                success: function(response) {
                    if (response.success) {
                        $(`.cart-item[data-product-id="${productId}"]`).fadeOut(300, function() {
                            $(this).remove();
                            
                            if ($('.cart-item').length === 0) {
                                location.reload();
                            }
                        });
                        
                        $('#cart-subtotal').text(response.subtotal);
                        $('#cart-tax').text(response.tax);
                        $('#cart-total').text(response.total);
                        
                        $('.cart-count').text(response.item_count);
                    }
                },
                error: function(xhr, status, error) {
                    console.error('Error removing item:', error);
                    alert('There was an error removing the item. Please try again.');
                }
            });
        }
    }
    
    $('input[name="payment_method"]').change(function() {
        if ($(this).val() === 'card') {
            $('#card_details').slideDown();
        } else {
            $('#card_details').slideUp();
        }
    });
    
    if ($('.counter').length > 0) {
        const counters = $('.counter');
        const animationDuration = 2000;
        
        counters.each(function() {
            const $this = $(this);
            const countTo = parseInt($this.text().replace(/,/g, ''));
            
            $({ countNum: 0 }).animate({
                countNum: countTo
            }, {
                duration: animationDuration,
                easing: 'swing',
                step: function() {
                    $this.text(Math.floor(this.countNum).toLocaleString());
                },
                complete: function() {
                    $this.text(countTo.toLocaleString());
                }
            });
        });
    }
    
    function validateForm(form) {
        let isValid = true;
        
        form.find('.is-invalid').removeClass('is-invalid');
        form.find('.invalid-feedback').remove();
        
        form.find('[required]').each(function() {
            const field = $(this);
            
            if (!field.val().trim()) {
                field.addClass('is-invalid');
                field.after('<div class="invalid-feedback">This field is required</div>');
                isValid = false;
            }
        });
        
        form.find('input[type="email"]').each(function() {
            const field = $(this);
            const emailRegex = /^[\w-\.]+@([\w-]+\.)+[\w-]{2,4}$/;
            
            if (field.val().trim() && !emailRegex.test(field.val().trim())) {
                field.addClass('is-invalid');
                field.after('<div class="invalid-feedback">Please enter a valid email address</div>');
                isValid = false;
            }
        });
        
        return isValid;
    }
    
    $('#contact-form').submit(function(e) {
        if (!validateForm($(this))) {
            e.preventDefault();
        }
    });
    
    $('#checkout-form').submit(function(e) {
        if (!validateForm($(this))) {
            e.preventDefault();
        }
    });
    
    $('.product-thumbnail').click(function() {
        const mainImage = $(this).data('image');
        $('.product-main-image').attr('src', mainImage);
    });
    
    $('#product-filter-form').submit(function(e) {
        e.preventDefault();
        
        const form = $(this);
        const url = form.attr('action');
        const formData = form.serialize();
        
        $.ajax({
            url: url,
            method: 'GET',
            data: formData,
            success: function(response) {
                $('#product-grid').html(response);
            },
            error: function(xhr, status, error) {
                console.error('Error filtering products:', error);
            }
        });
    });
    
    $('.carousel').carousel({
        interval: 5000
    });
    
    $('a.scroll-link').on('click', function(e) {
        e.preventDefault();
        
        const target = $(this.hash);
        
        if (target.length) {
            $('html, body').animate({
                scrollTop: target.offset().top - 70
            }, 800);
        }
    });
    
    const backToTopBtn = $('#back-to-top');
    
    $(window).scroll(function() {
        if ($(window).scrollTop() > 300) {
            backToTopBtn.addClass('show');
        } else {
            backToTopBtn.removeClass('show');
        }
    });
    
    backToTopBtn.click(function(e) {
        e.preventDefault();
        $('html, body').animate({scrollTop: 0}, 800);
    });
    
    $('#newsletter-form').submit(function(e) {
        e.preventDefault();
        
        const email = $('#newsletter-email').val().trim();
        const emailRegex = /^[\w-\.]+@([\w-]+\.)+[\w-]{2,4}$/;
        
        if (!email || !emailRegex.test(email)) {
            $('#newsletter-email').addClass('is-invalid');
            return;
        }
        
        $.ajax({
            url: '/subscribe',
            method: 'POST',
            data: {
                email: email
            },
            success: function(response) {
                $('#newsletter-form').html('<div class="alert alert-success">Thank you for subscribing!</div>');
            },
            error: function(xhr, status, error) {
                $('#newsletter-form').append('<div class="alert alert-danger mt-2">There was an error. Please try again.</div>');
            }
        });
    });
});