/**
 * SEO Helper Functions Module for Depanku Application
 * Provides dynamic title generation, meta description templates, structured data generation, and canonical URL generation
 */

class SEOHelper {
    constructor() {
        this.baseDomain = 'https://depanku.com';
        this.siteName = 'Depanku';
        this.siteDescription = 'AI-powered platform helping students discover STEM internships, research opportunities, and organizations for effective career planning.';
        this.defaultImage = '/static/images/og-landing.jpg';
        this.defaultImageWidth = 1200;
        this.defaultImageHeight = 630;
    }

    /**
     * Generate dynamic page title
     */
    generateTitle(pageTitle, options = {}) {
        const {
            separator = ' | ',
            includeSiteName = true,
            maxLength = 60
        } = options;

        let title = pageTitle;
        
        if (includeSiteName) {
            title = `${pageTitle}${separator}${this.siteName}`;
        }

        // Truncate if too long
        if (title.length > maxLength) {
            title = title.substring(0, maxLength - 3) + '...';
        }

        return title;
    }

    /**
     * Generate meta description
     */
    generateMetaDescription(content, options = {}) {
        const {
            maxLength = 160,
            includeCallToAction = true,
            template = null
        } = options;

        let description = content;

        // Use template if provided
        if (template) {
            description = this.applyTemplate(template, content);
        }

        // Add call to action if requested
        if (includeCallToAction) {
            description += ' Discover opportunities tailored to your interests today!';
        }

        // Truncate if too long
        if (description.length > maxLength) {
            description = description.substring(0, maxLength - 3) + '...';
        }

        return description;
    }

    /**
     * Generate Open Graph tags
     */
    generateOpenGraphTags(pageData, options = {}) {
        const {
            type = 'website',
            url = null,
            image = null,
            siteName = this.siteName,
            locale = 'en_US'
        } = options;

        const tags = {
            'og:title': this.generateTitle(pageData.title),
            'og:description': this.generateMetaDescription(pageData.description),
            'og:type': type,
            'og:url': url || this.generateCanonicalURL(pageData.path),
            'og:site_name': siteName,
            'og:locale': locale
        };

        // Add image if provided
        if (image) {
            tags['og:image'] = image.url;
            tags['og:image:width'] = image.width || this.defaultImageWidth;
            tags['og:image:height'] = image.height || this.defaultImageHeight;
            tags['og:image:alt'] = image.alt || pageData.title;
        } else if (pageData.image) {
            tags['og:image'] = pageData.image;
            tags['og:image:width'] = this.defaultImageWidth;
            tags['og:image:height'] = this.defaultImageHeight;
        }

        return tags;
    }

    /**
     * Generate Twitter Card tags
     */
    generateTwitterCardTags(pageData, options = {}) {
        const {
            card = 'summary_large_image',
            site = '@depanku',
            creator = '@depanku'
        } = options;

        const tags = {
            'twitter:card': card,
            'twitter:title': this.generateTitle(pageData.title),
            'twitter:description': this.generateMetaDescription(pageData.description),
            'twitter:site': site,
            'twitter:creator': creator
        };

        // Add image if provided
        if (pageData.image) {
            tags['twitter:image'] = pageData.image;
        }

        return tags;
    }

    /**
     * Generate canonical URL
     */
    generateCanonicalURL(path, options = {}) {
        const {
            includeParams = false,
            queryParams = {}
        } = options;

        let url = `${this.baseDomain}${path}`;

        if (includeParams && Object.keys(queryParams).length > 0) {
            const params = new URLSearchParams(queryParams);
            url += `?${params.toString()}`;
        }

        return url;
    }

    /**
     * Generate structured data for different content types
     */
    generateStructuredData(type, data) {
        switch (type) {
            case 'organization':
                return this.generateOrganizationStructuredData(data);
            case 'course':
                return this.generateCourseStructuredData(data);
            case 'article':
                return this.generateArticleStructuredData(data);
            case 'website':
                return this.generateWebsiteStructuredData(data);
            case 'breadcrumb':
                return this.generateBreadcrumbStructuredData(data);
            case 'search':
                return this.generateSearchStructuredData(data);
            default:
                return this.generateWebsiteStructuredData(data);
        }
    }

    /**
     * Generate organization structured data
     */
    generateOrganizationStructuredData(data) {
        return {
            "@context": "https://schema.org",
            "@type": "Organization",
            "name": data.name,
            "description": data.description,
            "url": data.url || this.generateCanonicalURL(`/organizations/${data.id}`),
            "logo": {
                "@type": "ImageObject",
                "url": data.logo || this.defaultImage
            },
            "image": {
                "@type": "ImageObject",
                "url": data.image || this.defaultImage
            },
            "address": {
                "@type": "PostalAddress",
                "streetAddress": data.address?.street,
                "addressLocality": data.address?.city,
                "addressRegion": data.address?.state,
                "postalCode": data.address?.zip,
                "addressCountry": data.address?.country || "US"
            },
            "contactPoint": {
                "@type": "ContactPoint",
                "telephone": data.contact?.phone,
                "contactType": data.contact?.type || "customer service",
                "email": data.contact?.email
            },
            "sameAs": data.socialLinks || [],
            "foundingDate": data.foundingDate,
            "numberOfEmployees": data.numberOfEmployees,
            "keywords": data.keywords
        };
    }

    /**
     * Generate course structured data
     */
    generateCourseStructuredData(data) {
        return {
            "@context": "https://schema.org",
            "@type": "Course",
            "name": data.title,
            "description": data.description,
            "provider": {
                "@type": "Organization",
                "name": data.provider || this.siteName,
                "url": this.baseDomain
            },
            "educationalLevel": data.educationalLevel,
            "courseCode": data.courseCode,
            "url": data.url || this.generateCanonicalURL(`/courses/${data.id}`),
            "image": data.image || this.defaultImage,
            "offers": {
                "@type": "Offer",
                "price": data.price,
                "priceCurrency": data.priceCurrency || "USD",
                "availability": "https://schema.org/InStock"
            },
            "duration": data.duration,
            "keywords": data.keywords
        };
    }

    /**
     * Generate article structured data
     */
    generateArticleStructuredData(data) {
        return {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": data.title,
            "description": data.description,
            "image": data.image || this.defaultImage,
            "author": {
                "@type": "Person",
                "name": data.author,
                "url": data.authorUrl
            },
            "publisher": {
                "@type": "Organization",
                "name": this.siteName,
                "logo": {
                    "@type": "ImageObject",
                    "url": this.baseDomain + "/static/images/logo.png"
                }
            },
            "datePublished": data.datePublished,
            "dateModified": data.dateModified,
            "mainEntityOfPage": {
                "@type": "WebPage",
                "@id": data.url || this.generateCanonicalURL(`/articles/${data.id}`)
            },
            "keywords": data.keywords
        };
    }

    /**
     * Generate website structured data
     */
    generateWebsiteStructuredData(data) {
        return {
            "@context": "https://schema.org",
            "@type": "WebSite",
            "name": this.siteName,
            "url": this.baseDomain,
            "description": this.siteDescription,
            "publisher": {
                "@type": "Organization",
                "name": this.siteName,
                "url": this.baseDomain,
                "logo": {
                    "@type": "ImageObject",
                    "url": this.baseDomain + "/static/images/logo.png"
                }
            },
            "potentialAction": {
                "@type": "SearchAction",
                "target": this.baseDomain + "/organizations?search={search_term_string}",
                "query-input": "required name=search_term_string"
            }
        };
    }

    /**
     * Generate breadcrumb structured data
     */
    generateBreadcrumbStructuredData(data) {
        const itemListElements = data.items.map((item, index) => ({
            "@type": "ListItem",
            "position": index + 1,
            "name": item.name,
            "item": item.url || this.generateCanonicalURL(item.path)
        }));

        return {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": itemListElements
        };
    }

    /**
     * Generate search structured data
     */
    generateSearchStructuredData(data) {
        return {
            "@context": "https://schema.org",
            "@type": "SearchResultsPage",
            "mainEntity": {
                "@type": "SearchAction",
                "target": this.baseDomain + "/organizations?search={search_term_string}",
                "query-input": "required name=search_term_string"
            },
            "name": data.title || "Search Results",
            "description": data.description || "Search results for organizations and opportunities"
        };
    }

    /**
     * Generate robots meta tag content
     */
    generateRobotsMetaTag(options = {}) {
        const {
            index = true,
            follow = true,
            maxSnippet = -1,
            maxImagePreview = 'large',
            maxVideoPreview = -1,
            noarchive = false,
            nosnippet = false,
            notranslate = false,
            noimageindex = false,
            unavailAfter = null
        } = options;

        const parts = [];

        if (index) parts.push('index');
        else parts.push('noindex');

        if (follow) parts.push('follow');
        else parts.push('nofollow');

        if (maxSnippet >= 0) parts.push(`max-snippet:${maxSnippet}`);
        if (maxImagePreview) parts.push(`max-image-preview:${maxImagePreview}`);
        if (maxVideoPreview >= 0) parts.push(`max-video-preview:${maxVideoPreview}`);

        if (noarchive) parts.push('noarchive');
        if (nosnippet) parts.push('nosnippet');
        if (notranslate) parts.push('notranslate');
        if (noimageindex) parts.push('noimageindex');
        if (unavailAfter) parts.push(`unavail-after:${unavailAfter}`);

        return parts.join(', ');
    }

    /**
     * Apply template to content
     */
    applyTemplate(template, content) {
        const templates = {
            organization: `${content} - ${this.siteName}: Discover ${content.toLowerCase()} opportunities and internships for students.`,
            course: `${content} course - Learn ${content.toLowerCase()} with expert instructors and hands-on projects.`,
            article: `${content} - Latest insights and tips from ${this.siteName} for career development.`,
            search: `Search results for "${content}" - Find organizations, courses, and opportunities matching your interests.`
        };

        return templates[template] || content;
    }

    /**
     * Generate sitemap URL
     */
    generateSitemapURL(options = {}) {
        const {
            includeImages = false,
            includeVideos = false,
            includeNews = false,
            sitemapIndex = false
        } = options;

        let path = '/sitemap.xml';
        
        if (sitemapIndex) {
            path = '/sitemap_index.xml';
        } else if (includeImages || includeVideos || includeNews) {
            const params = new URLSearchParams();
            if (includeImages) params.append('images', '1');
            if (includeVideos) params.append('videos', '1');
            if (includeNews) params.append('news', '1');
            path += `?${params.toString()}`;
        }

        return this.generateCanonicalURL(path);
    }

    /**
     * Generate meta tags for a page
     */
    generateMetaTags(pageData, options = {}) {
        const {
            includeOpenGraph = true,
            includeTwitter = true,
            includeStructuredData = true,
            includeCanonical = true,
            includeRobots = true
        } = options;

        const metaTags = {
            title: this.generateTitle(pageData.title),
            description: this.generateMetaDescription(pageData.description, {
                maxLength: 160,
                includeCallToAction: true
            })
        };

        // Add Open Graph tags
        if (includeOpenGraph) {
            metaTags.openGraph = this.generateOpenGraphTags(pageData, options);
        }

        // Add Twitter Card tags
        if (includeTwitter) {
            metaTags.twitter = this.generateTwitterCardTags(pageData, options);
        }

        // Add canonical URL
        if (includeCanonical) {
            metaTags.canonical = this.generateCanonicalURL(pageData.path);
        }

        // Add robots meta tag
        if (includeRobots) {
            metaTags.robots = this.generateRobotsMetaTag(options);
        }

        // Add structured data
        if (includeStructuredData && pageData.structuredDataType) {
            metaTags.structuredData = this.generateStructuredData(pageData.structuredDataType, pageData);
        }

        return metaTags;
    }

    /**
     * Generate URL-friendly slug
     */
    generateSlug(text) {
        return text
            .toLowerCase()
            .replace(/[^\w\s-]/g, '') // Remove special characters
            .replace(/\s+/g, '-') // Replace spaces with hyphens
            .replace(/-+/g, '-') // Replace multiple hyphens with single
            .trim('-'); // Remove leading/trailing hyphens
    }

    /**
     * Generate meta keywords from content
     */
    generateKeywords(content, options = {}) {
        const {
            maxLength = 10,
            excludeCommonWords = true,
            minLength = 3
        } = options;

        const commonWords = ['the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 'how', 'its', 'may', 'new', 'now', 'old', 'see', 'two', 'way', 'who', 'boy', 'did', 'does', 'let', 'put', 'say', 'she', 'too', 'use'];
        
        // Extract words from content
        const words = content
            .toLowerCase()
            .replace(/[^\w\s]/g, ' ')
            .split(/\s+/)
            .filter(word => word.length >= minLength);

        // Count word frequency
        const wordCount = {};
        words.forEach(word => {
            if (!excludeCommonWords || !commonWords.includes(word)) {
                wordCount[word] = (wordCount[word] || 0) + 1;
            }
        });

        // Sort by frequency and take top words
        const sortedWords = Object.entries(wordCount)
            .sort(([,a], [,b]) => b - a)
            .slice(0, maxLength)
            .map(([word]) => word);

        return sortedWords.join(', ');
    }

    /**
     * Generate alt text for images
     */
    generateAltText(imageData, options = {}) {
        const {
            includeContext = true,
            maxLength = 125
        } = options;

        let altText = imageData.description || imageData.title || '';

        if (includeContext && imageData.context) {
            altText = `${imageData.context}: ${altText}`;
        }

        // Truncate if too long
        if (altText.length > maxLength) {
            altText = altText.substring(0, maxLength - 3) + '...';
        }

        return altText;
    }
}

// Initialize SEO helper when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    const seoHelper = new SEOHelper();
    
    // Make it globally available
    window.SEOHelper = SEOHelper;
    window.seoHelper = seoHelper;
    
    // Example usage: Update page meta tags dynamically
    if (window.pageData) {
        const metaTags = seoHelper.generateMetaTags(window.pageData);
        seoHelper.updatePageMetaTags(metaTags);
    }
});

// Export for use in other modules
window.SEOHelper = SEOHelper;

/**
 * Helper function to update page meta tags
 */
function updatePageMetaTags(metaTags) {
    // Update title
    if (metaTags.title) {
        document.title = metaTags.title;
    }

    // Update description
    if (metaTags.description) {
        const descriptionMeta = document.querySelector('meta[name="description"]');
        if (descriptionMeta) {
            descriptionMeta.setAttribute('content', metaTags.description);
        }
    }

    // Update Open Graph tags
    if (metaTags.openGraph) {
        Object.entries(metaTags.openGraph).forEach(([property, content]) => {
            const meta = document.querySelector(`meta[property="${property}"]`);
            if (meta) {
                meta.setAttribute('content', content);
            } else {
                const newMeta = document.createElement('meta');
                newMeta.setAttribute('property', property);
                newMeta.setAttribute('content', content);
                document.head.appendChild(newMeta);
            }
        });
    }

    // Update Twitter Card tags
    if (metaTags.twitter) {
        Object.entries(metaTags.twitter).forEach(([name, content]) => {
            const meta = document.querySelector(`meta[name="${name}"]`);
            if (meta) {
                meta.setAttribute('content', content);
            } else {
                const newMeta = document.createElement('meta');
                newMeta.setAttribute('name', name);
                newMeta.setAttribute('content', content);
                document.head.appendChild(newMeta);
            }
        });
    }

    // Update canonical URL
    if (metaTags.canonical) {
        let canonicalLink = document.querySelector('link[rel="canonical"]');
        if (canonicalLink) {
            canonicalLink.setAttribute('href', metaTags.canonical);
        } else {
            canonicalLink = document.createElement('link');
            canonicalLink.setAttribute('rel', 'canonical');
            canonicalLink.setAttribute('href', metaTags.canonical);
            document.head.appendChild(canonicalLink);
        }
    }

    // Update robots meta tag
    if (metaTags.robots) {
        let robotsMeta = document.querySelector('meta[name="robots"]');
        if (robotsMeta) {
            robotsMeta.setAttribute('content', metaTags.robots);
        } else {
            robotsMeta = document.createElement('meta');
            robotsMeta.setAttribute('name', 'robots');
            robotsMeta.setAttribute('content', metaTags.robots);
            document.head.appendChild(robotsMeta);
        }
    }

    // Update structured data
    if (metaTags.structuredData) {
        let structuredDataScript = document.querySelector('script[type="application/ld+json"]');
        if (structuredDataScript) {
            structuredDataScript.textContent = JSON.stringify(metaTags.structuredData, null, 2);
        } else {
            structuredDataScript = document.createElement('script');
            structuredDataScript.setAttribute('type', 'application/ld+json');
            structuredDataScript.textContent = JSON.stringify(metaTags.structuredData, null, 2);
            document.head.appendChild(structuredDataScript);
        }
    }
}