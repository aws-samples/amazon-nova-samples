document.addEventListener('DOMContentLoaded', () => {
    // Navigation and section display
    const navLinks = document.querySelectorAll('.nav-links a');
    const sections = document.querySelectorAll('main section');
    
    function showSection(sectionId) {
        // Hide all sections
        sections.forEach(section => {
            section.classList.remove('active-section');
        });
        
        // Show the selected section
        const activeSection = document.querySelector(sectionId);
        if (activeSection) {
            activeSection.classList.add('active-section');
        }
        
        // Update nav links
        navLinks.forEach(link => {
            link.classList.toggle('active', link.getAttribute('href') === sectionId);
        });
    }
    
    // Set up navigation click handlers
    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const sectionId = link.getAttribute('href');
            showSection(sectionId);
            
            // Add to browser history
            history.pushState(null, null, sectionId);
        });
    });
    
    // Mock product data
    const products = [
        // Electronics
        { id: 1, title: 'Premium Smartphone', price: 699, category: 'electronics', subcategory: 'phones', featured: true, description: 'Latest model with high-resolution camera and all-day battery life', image: 'images/smartphone.jpg', rating: 4.5, stock: 42 },
        { id: 2, title: 'Ultra Thin Laptop', price: 1299, category: 'electronics', subcategory: 'computers', featured: true, description: 'Powerful processor with SSD storage and stunning display', image: 'images/laptop.jpg', rating: 4.7, stock: 15 },
        { id: 3, title: 'Noise Cancelling Headphones', price: 199, category: 'electronics', subcategory: 'audio', featured: false, description: 'Immersive sound experience with wireless connectivity', image: 'images/headphones.jpg', rating: 4.3, stock: 28 },
        { id: 4, title: 'Smart Watch Series 5', price: 299, category: 'electronics', subcategory: 'wearables', featured: true, description: 'Track your fitness and stay connected on the go', image: 'images/smartwatch.jpg', rating: 4.2, stock: 20 },
        { id: 5, title: 'Professional Tablet', price: 499, category: 'electronics', subcategory: 'computers', featured: true, description: 'Perfect for creative professionals and note-taking', image: 'images/tablet.jpg', rating: 4.6, stock: 13 },
        { id: 6, title: '4K Ultra HD TV', price: 849, category: 'electronics', subcategory: 'home', featured: false, description: 'Stunning picture quality with smart capabilities', image: 'images/tv.jpg', rating: 4.4, stock: 7 },
        { id: 7, title: 'Wireless Earbuds', price: 129, category: 'electronics', subcategory: 'audio', featured: false, description: 'Crystal clear sound in a compact design', image: 'images/earbuds.jpg', rating: 4.1, stock: 35 },
        { id: 8, title: 'Digital Camera', price: 599, category: 'electronics', subcategory: 'cameras', featured: false, description: 'Capture life\'s moments in stunning detail', image: 'images/camera.jpg', rating: 4.3, stock: 10 },
        
        // Clothing
        { id: 9, title: 'Premium Cotton T-shirt', price: 29, category: 'clothing', subcategory: 'tops', featured: false, description: 'Comfortable and stylish for everyday wear', image: 'images/tshirt.jpg', rating: 4.0, stock: 50 },
        { id: 10, title: 'Designer Jeans', price: 89, category: 'clothing', subcategory: 'pants', featured: true, description: 'Perfect fit with premium denim material', image: 'images/jeans.jpg', rating: 4.5, stock: 22 },
        { id: 11, title: 'Running Sneakers', price: 119, category: 'clothing', subcategory: 'shoes', featured: true, description: 'Lightweight with superior cushioning', image: 'images/sneakers.jpg', rating: 4.7, stock: 18 },
        { id: 12, title: 'Summer Dress', price: 79, category: 'clothing', subcategory: 'dresses', featured: false, description: 'Elegant design perfect for warm weather', image: 'images/dress.jpg', rating: 4.2, stock: 15 },
        { id: 13, title: 'Winter Jacket', price: 159, category: 'clothing', subcategory: 'outerwear', featured: false, description: 'Stay warm with this insulated and waterproof design', image: 'images/jacket.jpg', rating: 4.6, stock: 12 },
        { id: 14, title: 'Formal Shirt', price: 59, category: 'clothing', subcategory: 'tops', featured: false, description: 'Classic design for professional settings', image: 'images/formal-shirt.jpg', rating: 4.1, stock: 25 },
        { id: 15, title: 'Yoga Pants', price: 49, category: 'clothing', subcategory: 'pants', featured: false, description: 'Flexible material perfect for workouts', image: 'images/yoga-pants.jpg', rating: 4.4, stock: 30 },
        { id: 16, title: 'Leather Boots', price: 149, category: 'clothing', subcategory: 'shoes', featured: false, description: 'Durable and stylish for all seasons', image: 'images/boots.jpg', rating: 4.3, stock: 8 },
        
        // Books
        { id: 17, title: 'Bestselling Novel', price: 15, category: 'books', subcategory: 'fiction', featured: false, description: 'Award-winning story that will keep you engaged', image: 'images/novel.jpg', rating: 4.8, stock: 40 },
        { id: 18, title: 'Gourmet Cookbook', price: 25, category: 'books', subcategory: 'cooking', featured: true, description: 'Collection of recipes from around the world', image: 'images/cookbook.jpg', rating: 4.5, stock: 15 },
        { id: 19, title: 'World History Collection', price: 34, category: 'books', subcategory: 'non-fiction', featured: false, description: 'Comprehensive look at major historical events', image: 'images/history.jpg', rating: 4.6, stock: 12 },
        { id: 20, title: 'Sci-Fi Anthology', price: 22, category: 'books', subcategory: 'fiction', featured: false, description: 'Collection of futuristic short stories', image: 'images/scifi.jpg', rating: 4.3, stock: 18 },
        { id: 21, title: 'Self-Help Guide', price: 19, category: 'books', subcategory: 'non-fiction', featured: true, description: 'Practical advice for personal growth', image: 'images/self-help.jpg', rating: 4.4, stock: 25 },
        
        // Home & Kitchen
        { id: 22, title: 'Stainless Steel Blender', price: 79, category: 'home', subcategory: 'appliances', featured: true, description: 'Powerful motor with multiple speed settings', image: 'images/blender.jpg', rating: 4.2, stock: 14 },
        { id: 23, title: 'Ceramic Dinnerware Set', price: 129, category: 'home', subcategory: 'kitchen', featured: false, description: 'Elegant 16-piece set for family dining', image: 'images/dinnerware.jpg', rating: 4.5, stock: 8 },
        { id: 24, title: 'Queen Size Bedding Set', price: 99, category: 'home', subcategory: 'bedroom', featured: false, description: 'Soft cotton with modern patterns', image: 'images/bedding.jpg', rating: 4.4, stock: 10 },
        { id: 25, title: 'Aromatherapy Diffuser', price: 45, category: 'home', subcategory: 'decor', featured: true, description: 'Create a calming atmosphere with essential oils', image: 'images/diffuser.jpg', rating: 4.3, stock: 20 },
        
        // Sports & Outdoors
        { id: 26, title: 'Mountain Bike', price: 499, category: 'sports', subcategory: 'cycling', featured: true, description: 'Durable frame with premium components', image: 'images/bike.jpg', rating: 4.7, stock: 5 },
        { id: 27, title: 'Yoga Mat', price: 29, category: 'sports', subcategory: 'fitness', featured: false, description: 'Non-slip surface for comfortable practice', image: 'images/yoga-mat.jpg', rating: 4.4, stock: 30 },
        { id: 28, title: 'Camping Tent', price: 149, category: 'sports', subcategory: 'outdoors', featured: false, description: 'Waterproof design fits up to 4 people', image: 'images/tent.jpg', rating: 4.3, stock: 12 },
        { id: 29, title: 'Basketball', price: 25, category: 'sports', subcategory: 'team sports', featured: false, description: 'Official size and weight for indoor/outdoor play', image: 'images/basketball.jpg', rating: 4.5, stock: 25 },
        
        // Beauty & Personal Care
        { id: 30, title: 'Skincare Collection', price: 89, category: 'beauty', subcategory: 'skincare', featured: true, description: 'Complete regimen for radiant skin', image: 'images/skincare.jpg', rating: 4.6, stock: 15 },
        { id: 31, title: 'Hair Styling Kit', price: 149, category: 'beauty', subcategory: 'hair care', featured: false, description: 'Professional tools for salon-quality styling', image: 'images/hairstyling.jpg', rating: 4.4, stock: 10 },
        { id: 32, title: 'Fragrance Gift Set', price: 69, category: 'beauty', subcategory: 'fragrance', featured: false, description: 'Collection of premium scents', image: 'images/fragrance.jpg', rating: 4.2, stock: 18 }
    ];
    
    // Create product cards
    function createProductCard(product) {
        const card = document.createElement('div');
        card.className = 'product-card';
        card.setAttribute('data-testid', `product-${product.id}`);
        card.setAttribute('data-product-id', product.id);
        card.setAttribute('data-product-category', product.category);
        card.setAttribute('data-product-price', product.price);
        
        // Create product image
        const imageDiv = document.createElement('div');
        imageDiv.className = 'product-image';
        
        // Use placeholder images with background color based on category
        let bgColor;
        switch(product.category) {
            case 'electronics': bgColor = '#e0f7fa'; break;
            case 'clothing': bgColor = '#f3e5f5'; break;
            case 'books': bgColor = '#fff8e1'; break;
            case 'home': bgColor = '#e8f5e9'; break;
            case 'sports': bgColor = '#e3f2fd'; break;
            case 'beauty': bgColor = '#fce4ec'; break;
            default: bgColor = '#f5f5f5';
        }
        
        // Create the product image or fallback
        if (product.image) {
            const image = document.createElement('img');
            image.className = 'product-image-img';
            image.src = product.image;
            image.alt = `${product.title}`;
            imageDiv.appendChild(image);
        } else {
            const placeholder = document.createElement('div');
            placeholder.className = 'product-image-placeholder';
            placeholder.style.backgroundColor = bgColor;
            // semgrep:skip=javascript.browser.security.insecure-user-controlled-data-in-methods-like-innerhtml: Using controlled data from product title first character only
            placeholder.innerHTML = `<div class="product-image-icon">${product.title.charAt(0)}</div>`;
            placeholder.setAttribute('aria-label', `${product.title} image`);
            imageDiv.appendChild(placeholder);
        }
        
        // Create badge for featured products
        if (product.featured) {
            const featuredBadge = document.createElement('div');
            featuredBadge.className = 'featured-badge';
            featuredBadge.textContent = 'Featured';
            imageDiv.appendChild(featuredBadge);
        }
        
        // Create product info container
        const infoDiv = document.createElement('div');
        infoDiv.className = 'product-info';
        
        // Add product title
        const title = document.createElement('div');
        title.className = 'product-title';
        title.textContent = product.title;
        
        // Add rating
        const ratingDiv = document.createElement('div');
        ratingDiv.className = 'product-rating';
        
        // Create star rating
        const rating = product.rating || 0;
        const fullStars = Math.floor(rating);
        const hasHalfStar = rating % 1 >= 0.5;
        
        const starsContainer = document.createElement('div');
        starsContainer.className = 'stars';
        
        // Add full stars
        for (let i = 0; i < fullStars; i++) {
            const star = document.createElement('span');
            star.className = 'star full';
            star.innerHTML = '★';
            starsContainer.appendChild(star);
        }
        
        // Add half star if needed
        if (hasHalfStar) {
            const halfStar = document.createElement('span');
            halfStar.className = 'star half';
            halfStar.innerHTML = '★';
            starsContainer.appendChild(halfStar);
        }
        
        // Add empty stars to make it 5 stars total
        const emptyStars = 5 - fullStars - (hasHalfStar ? 1 : 0);
        for (let i = 0; i < emptyStars; i++) {
            const emptyStar = document.createElement('span');
            emptyStar.className = 'star empty';
            emptyStar.innerHTML = '☆';
            starsContainer.appendChild(emptyStar);
        }
        
        // Add numeric rating
        const ratingText = document.createElement('span');
        ratingText.className = 'rating-text';
        ratingText.textContent = ` ${rating.toFixed(1)}`;
        
        ratingDiv.appendChild(starsContainer);
        ratingDiv.appendChild(ratingText);
        
        // Add category and subcategory
        const category = document.createElement('div');
        category.className = 'product-category';
        category.textContent = product.subcategory ? 
            `${product.category} > ${product.subcategory}` : 
            product.category;
        
        // Add description if available
        let description;
        if (product.description) {
            description = document.createElement('div');
            description.className = 'product-description';
            description.textContent = product.description;
        }
        
        // Add price and stock information
        const priceStockDiv = document.createElement('div');
        priceStockDiv.className = 'price-stock';
        
        const price = document.createElement('div');
        price.className = 'product-price';
        price.textContent = `$${product.price}`;
        
        const stock = document.createElement('div');
        stock.className = 'product-stock';
        if (product.stock > 0) {
            stock.textContent = `${product.stock} in stock`;
            stock.classList.add('in-stock');
        } else {
            stock.textContent = 'Out of stock';
            stock.classList.add('out-of-stock');
        }
        
        priceStockDiv.appendChild(price);
        priceStockDiv.appendChild(stock);
        
        // Add to cart button
        const addToCartBtn = document.createElement('button');
        addToCartBtn.className = 'add-to-cart';
        addToCartBtn.textContent = 'Add to Cart';
        addToCartBtn.setAttribute('data-testid', `add-to-cart-${product.id}`);
        addToCartBtn.disabled = product.stock <= 0;
        
        addToCartBtn.addEventListener('click', () => {
            showNotification(`Added ${product.title} to cart!`);
        });
        
        // Quick view button
        const quickViewBtn = document.createElement('button');
        quickViewBtn.className = 'quick-view';
        quickViewBtn.textContent = 'Quick View';
        quickViewBtn.setAttribute('data-testid', `quick-view-${product.id}`);
        
        quickViewBtn.addEventListener('click', () => {
            showNotification(`Quick view for ${product.title}`);
        });
        
        // Create buttons container
        const buttonsDiv = document.createElement('div');
        buttonsDiv.className = 'product-buttons';
        buttonsDiv.appendChild(addToCartBtn);
        buttonsDiv.appendChild(quickViewBtn);
        
        // Assemble the product card
        infoDiv.appendChild(title);
        infoDiv.appendChild(ratingDiv);
        infoDiv.appendChild(category);
        if (description) {
            infoDiv.appendChild(description);
        }
        infoDiv.appendChild(priceStockDiv);
        infoDiv.appendChild(buttonsDiv);
        
        card.appendChild(imageDiv);
        card.appendChild(infoDiv);
        
        return card;
    }
    
    // Load featured products
    function loadFeaturedProducts() {
        const featuredGrid = document.getElementById('featured-products-grid');
        featuredGrid.innerHTML = '';
        
        const featuredProducts = products.filter(p => p.featured);
        featuredProducts.forEach(product => {
            featuredGrid.appendChild(createProductCard(product));
        });
    }
    
    // Load all products (paginated)
    let currentPage = 1;
    const productsPerPage = 6;
    let filteredProducts = [...products];
    
    function loadProducts() {
        const productsGrid = document.getElementById('products-grid');
        productsGrid.innerHTML = '';
        
        const startIndex = (currentPage - 1) * productsPerPage;
        const paginatedProducts = filteredProducts.slice(startIndex, startIndex + productsPerPage);
        
        if (paginatedProducts.length === 0) {
            const noProducts = document.createElement('div');
            noProducts.textContent = 'No products found.';
            noProducts.setAttribute('data-testid', 'no-products');
            productsGrid.appendChild(noProducts);
        } else {
            paginatedProducts.forEach(product => {
                productsGrid.appendChild(createProductCard(product));
            });
        }
        
        // Update pagination
        document.getElementById('page-indicator').textContent = 
            `Page ${currentPage} of ${Math.ceil(filteredProducts.length / productsPerPage)}`;
        
        document.getElementById('prev-page').disabled = currentPage === 1;
        document.getElementById('next-page').disabled = 
            currentPage >= Math.ceil(filteredProducts.length / productsPerPage);
    }
    
    // Apply filters and sorting
    function applyFilters() {
        const categoryFilter = document.getElementById('category-filter').value;
        const subcategoryFilter = document.getElementById('subcategory-filter').value;
        const priceFilter = parseInt(document.getElementById('price-range').value);
        const sortBy = document.getElementById('sort-by').value;
        
        // Filter products
        filteredProducts = products.filter(product => {
            const matchesCategory = categoryFilter === '' || product.category === categoryFilter;
            const matchesSubcategory = subcategoryFilter === '' || product.subcategory === subcategoryFilter;
            const matchesPrice = product.price <= priceFilter;
            return matchesCategory && matchesSubcategory && matchesPrice;
        });
        
        // Sort products
        switch (sortBy) {
            case 'price-low':
                filteredProducts.sort((a, b) => a.price - b.price);
                break;
            case 'price-high':
                filteredProducts.sort((a, b) => b.price - a.price);
                break;
            case 'rating':
                filteredProducts.sort((a, b) => (b.rating || 0) - (a.rating || 0));
                break;
            case 'newest':
                filteredProducts.sort((a, b) => b.id - a.id); // Assuming higher IDs are newer products
                break;
            default: // relevance or default
                // For relevance, show featured items first, then sort by rating
                filteredProducts.sort((a, b) => {
                    if (a.featured && !b.featured) return -1;
                    if (!a.featured && b.featured) return 1;
                    return (b.rating || 0) - (a.rating || 0);
                });
        }
        
        currentPage = 1;
        loadProducts();
    }
    
    // Update subcategory filter based on selected category
    function updateSubcategoryFilter() {
        const categoryFilter = document.getElementById('category-filter').value;
        const subcategoryFilter = document.getElementById('subcategory-filter');
        
        // Clear existing options
        while (subcategoryFilter.options.length > 1) {
            subcategoryFilter.remove(1);
        }
        
        // Enable/disable and update label
        if (categoryFilter === '') {
            subcategoryFilter.disabled = true;
            subcategoryFilter.options[0].text = 'Select Category First';
            return;
        }
        
        // Get unique subcategories for selected category
        const subcategories = new Set();
        products.forEach(product => {
            if (product.category === categoryFilter && product.subcategory) {
                subcategories.add(product.subcategory);
            }
        });
        
        // Enable and update label
        subcategoryFilter.disabled = false;
        subcategoryFilter.options[0].text = 'All Subcategories';
        
        // Add subcategory options
        Array.from(subcategories).sort().forEach(subcategory => {
            const option = document.createElement('option');
            option.value = subcategory;
            option.textContent = subcategory.charAt(0).toUpperCase() + subcategory.slice(1);
            subcategoryFilter.appendChild(option);
        });
    }
    
    // Set up filters and sorting
    document.getElementById('category-filter').addEventListener('change', () => {
        updateSubcategoryFilter();
        applyFilters();
    });
    
    document.getElementById('subcategory-filter').addEventListener('change', applyFilters);
    
    document.getElementById('price-range').addEventListener('input', (e) => {
        document.getElementById('price-value').textContent = `$${e.target.value}`;
        applyFilters();
    });
    
    document.getElementById('sort-by').addEventListener('change', applyFilters);
    
    // Pagination buttons
    document.getElementById('prev-page').addEventListener('click', () => {
        if (currentPage > 1) {
            currentPage--;
            loadProducts();
        }
    });
    
    document.getElementById('next-page').addEventListener('click', () => {
        if (currentPage < Math.ceil(filteredProducts.length / productsPerPage)) {
            currentPage++;
            loadProducts();
        }
    });
    
    // Search functionality
    document.getElementById('search-btn').addEventListener('click', () => {
        performSearch();
    });
    
    document.getElementById('search-input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            performSearch();
        }
    });
    
    function performSearch() {
        const searchTerm = document.getElementById('search-input').value.toLowerCase().trim();
        if (searchTerm) {
            showSection('#products');
            
            filteredProducts = products.filter(product => {
                return product.title.toLowerCase().includes(searchTerm) || 
                       product.category.toLowerCase().includes(searchTerm);
            });
            
            currentPage = 1;
            loadProducts();
        }
    }
    
    // Modal functionality
    const loginModal = document.getElementById('login-modal');
    const loginBtn = document.getElementById('login-btn');
    const closeModal = document.querySelector('.close-modal');
    
    loginBtn.addEventListener('click', () => {
        loginModal.style.display = 'block';
    });
    
    closeModal.addEventListener('click', () => {
        loginModal.style.display = 'none';
    });
    
    window.addEventListener('click', (e) => {
        if (e.target === loginModal) {
            loginModal.style.display = 'none';
        }
    });
    
    // Form submissions
    const loginForm = document.getElementById('login-form');
    const contactForm = document.getElementById('contact-form');
    
    loginForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const username = document.getElementById('username').value;
        loginModal.style.display = 'none';
        showNotification(`Welcome, ${username}!`);
        loginBtn.textContent = username;
        loginBtn.disabled = true;
    });
    
    contactForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const name = document.getElementById('name').value;
        showNotification(`Thank you for your message, ${name}! We'll get back to you soon.`);
        contactForm.reset();
    });
    
    // Register link
    document.getElementById('register-link').addEventListener('click', (e) => {
        e.preventDefault();
        showNotification('Registration functionality is not implemented in this demo.');
    });
    
    // Notifications
    function showNotification(message, isError = false) {
        const notification = document.getElementById('notification');
        notification.textContent = message;
        notification.className = isError ? 'notification error show' : 'notification show';
        
        setTimeout(() => {
            notification.classList.remove('show');
        }, 3000);
    }
    
    // Load initial data
    loadFeaturedProducts();
    loadProducts();
    
    // Check for hash in URL
    if (window.location.hash) {
        showSection(window.location.hash);
    } else {
        showSection('#home');
    }
    
    // Add debug feature (accessible via console)
    window.qaTestApp = {
        getProducts: () => products,
        addProduct: (product) => {
            products.push({
                id: products.length + 1,
                ...product
            });
            loadProducts();
            if (product.featured) {
                loadFeaturedProducts();
            }
            return products;
        },
        triggerError: (message) => {
            showNotification(message || 'An error occurred!', true);
        }
    };
});
