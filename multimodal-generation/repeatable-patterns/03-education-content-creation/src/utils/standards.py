"""
Standards Database Module

Educational standards database and management system for curriculum alignment.
"""

import logging

# Configure logging
logger = logging.getLogger(__name__)


class StandardsDatabase:
    """Educational standards database and management system."""
    
    def __init__(self):
        self.standards = self._initialize_sample_standards()
    
    def _initialize_sample_standards(self):
        """Initialize with sample standards data."""
        return {
            "8th_grade_mathematics": [
                {
                    "code": "8.EE.A.1",
                    "description": "Know and apply the properties of integer exponents to generate equivalent numerical expressions.",
                    "keywords": ["exponents", "properties", "integer", "numerical expressions"],
                    "grade": 8,
                    "subject": "mathematics",
                    "domain": "Expressions and Equations"
                },
                {
                    "code": "8.EE.A.2",
                    "description": "Use square root and cube root symbols to represent solutions to equations.",
                    "keywords": ["square root", "cube root", "equations", "solutions"],
                    "grade": 8,
                    "subject": "mathematics",
                    "domain": "Expressions and Equations"
                },
                {
                    "code": "8.G.A.1",
                    "description": "Verify experimentally the properties of rotations, reflections, and translations.",
                    "keywords": ["rotations", "reflections", "translations", "transformations"],
                    "grade": 8,
                    "subject": "mathematics",
                    "domain": "Geometry"
                }
            ],
            "11th_grade_mathematics": [
                {
                    "code": "A-REI.B.3",
                    "description": "Solve linear equations and inequalities in one variable, including equations with coefficients represented by letters.",
                    "keywords": ["linear equations", "inequalities", "coefficients", "variables"],
                    "grade": 11,
                    "subject": "mathematics",
                    "domain": "Algebra"
                },
                {
                    "code": "F-IF.C.7",
                    "description": "Graph functions expressed symbolically and show key features of the graph.",
                    "keywords": ["graph functions", "symbolic", "key features", "analysis"],
                    "grade": 11,
                    "subject": "mathematics",
                    "domain": "Functions"
                },
                {
                    "code": "S-ID.B.6",
                    "description": "Represent data on two quantitative variables on a scatter plot, and describe how the variables are related.",
                    "keywords": ["scatter plot", "quantitative variables", "data representation", "correlation"],
                    "grade": 11,
                    "subject": "mathematics",
                    "domain": "Statistics"
                }
            ],
            "8th_grade_science": [
                {
                    "code": "MS-PS1-1",
                    "description": "Develop models to describe the atomic composition of simple molecules and extended structures.",
                    "keywords": ["atomic composition", "molecules", "models", "structures"],
                    "grade": 8,
                    "subject": "science",
                    "domain": "Physical Science"
                },
                {
                    "code": "MS-LS1-5",
                    "description": "Construct a scientific explanation based on evidence for how environmental and genetic factors influence the growth of organisms.",
                    "keywords": ["environmental factors", "genetic factors", "organism growth", "scientific explanation"],
                    "grade": 8,
                    "subject": "science",
                    "domain": "Life Science"
                }
            ],
            "11th_grade_science": [
                {
                    "code": "HS-PS1-1",
                    "description": "Use the periodic table as a model to predict the relative properties of elements based on the patterns of electrons in the outermost energy level of atoms.",
                    "keywords": ["periodic table", "electron patterns", "atomic properties", "energy levels"],
                    "grade": 11,
                    "subject": "science",
                    "domain": "Physical Science"
                },
                {
                    "code": "HS-LS2-1",
                    "description": "Use mathematical and/or computational representations to support explanations of factors that affect carrying capacity of ecosystems at different scales.",
                    "keywords": ["carrying capacity", "ecosystems", "mathematical representations", "environmental factors"],
                    "grade": 11,
                    "subject": "science",
                    "domain": "Life Science"
                }
            ]
        }
    
    def get_standards_for_grade(self, grade, subject="mathematics"):
        """Get standards for a specific grade and subject."""
        key = f"{grade}th_grade_{subject}"
        standards = self.standards.get(key, [])
        
        if not standards:
            logger.warning(f"No standards found for grade {grade} {subject}")
            # Return empty list but log the attempt
            return []
        
        logger.info(f"Retrieved {len(standards)} standards for grade {grade} {subject}")
        return standards
    
    def get_standards_by_domain(self, grade, subject, domain):
        """Get standards for a specific domain within a grade and subject."""
        all_standards = self.get_standards_for_grade(grade, subject)
        domain_standards = [s for s in all_standards if s.get('domain', '').lower() == domain.lower()]
        
        logger.info(f"Retrieved {len(domain_standards)} standards for {domain} in grade {grade} {subject}")
        return domain_standards
    
    def search_standards_by_keyword(self, keyword, grade=None, subject=None):
        """Search for standards containing specific keywords."""
        matching_standards = []
        
        for key, standards_list in self.standards.items():
            # Filter by grade and subject if specified
            if grade and f"{grade}th_grade" not in key:
                continue
            if subject and subject not in key:
                continue
                
            for standard in standards_list:
                # Check if keyword appears in description or keywords list
                if (keyword.lower() in standard['description'].lower() or 
                    any(keyword.lower() in kw.lower() for kw in standard.get('keywords', []))):
                    matching_standards.append(standard)
        
        logger.info(f"Found {len(matching_standards)} standards matching keyword '{keyword}'")
        return matching_standards
    
    def compare_grade_standards(self, grade1, grade2, subject="mathematics"):
        """Compare standards between two grade levels."""
        standards1 = self.get_standards_for_grade(grade1, subject)
        standards2 = self.get_standards_for_grade(grade2, subject)
        
        return {
            f"grade_{grade1}": {
                "count": len(standards1),
                "standards": standards1,
                "complexity_level": self._assess_complexity_level(standards1)
            },
            f"grade_{grade2}": {
                "count": len(standards2),
                "standards": standards2,
                "complexity_level": self._assess_complexity_level(standards2)
            },
            "progression_analysis": self._analyze_progression(standards1, standards2)
        }
    
    def _assess_complexity_level(self, standards):
        """Assess the complexity level of a set of standards."""
        if not standards:
            return "No standards available"
        
        complexity_indicators = {
            "basic": ["know", "identify", "recognize", "recall", "describe"],
            "intermediate": ["apply", "use", "solve", "calculate", "explain", "compare"],
            "advanced": ["analyze", "evaluate", "synthesize", "create", "design", "construct"]
        }
        
        complexity_scores = {"basic": 0, "intermediate": 0, "advanced": 0}
        
        for standard in standards:
            description_lower = standard["description"].lower()
            for level, indicators in complexity_indicators.items():
                if any(indicator in description_lower for indicator in indicators):
                    complexity_scores[level] += 1
        
        # Determine overall complexity
        if complexity_scores["advanced"] > complexity_scores["intermediate"]:
            return "Advanced"
        elif complexity_scores["intermediate"] > complexity_scores["basic"]:
            return "Intermediate"
        else:
            return "Basic"
    
    def _analyze_progression(self, standards1, standards2):
        """Analyze the progression between two sets of standards."""
        if not standards1 or not standards2:
            return {"error": "Cannot analyze progression with empty standards sets"}
        
        # Simple analysis based on complexity indicators
        complexity1 = self._assess_complexity_level(standards1)
        complexity2 = self._assess_complexity_level(standards2)
        
        # Count domain overlap
        domains1 = set(s.get('domain', '') for s in standards1)
        domains2 = set(s.get('domain', '') for s in standards2)
        common_domains = domains1.intersection(domains2)
        
        return {
            "complexity_progression": f"{complexity1} → {complexity2}",
            "domain_overlap": len(common_domains),
            "common_domains": list(common_domains),
            "new_domains": list(domains2 - domains1),
            "progression_type": self._determine_progression_type(complexity1, complexity2)
        }
    
    def _determine_progression_type(self, complexity1, complexity2):
        """Determine the type of progression between complexity levels."""
        complexity_order = ["Basic", "Intermediate", "Advanced"]
        
        try:
            index1 = complexity_order.index(complexity1)
            index2 = complexity_order.index(complexity2)
            
            if index2 > index1:
                return "Progressive (increasing complexity)"
            elif index2 < index1:
                return "Regressive (decreasing complexity)"
            else:
                return "Stable (same complexity level)"
        except ValueError:
            return "Unknown progression"
    
    def add_custom_standard(self, grade, subject, standard_data):
        """Add a custom standard to the database."""
        key = f"{grade}th_grade_{subject}"
        
        if key not in self.standards:
            self.standards[key] = []
        
        # Validate required fields
        required_fields = ['code', 'description', 'keywords']
        if not all(field in standard_data for field in required_fields):
            raise ValueError(f"Standard must include: {required_fields}")
        
        # Add grade and subject if not present
        standard_data['grade'] = grade
        standard_data['subject'] = subject
        
        self.standards[key].append(standard_data)
        logger.info(f"Added custom standard {standard_data['code']} for grade {grade} {subject}")
    
    def get_all_subjects(self):
        """Get list of all available subjects."""
        subjects = set()
        for key in self.standards.keys():
            if '_grade_' in key:
                subject = key.split('_grade_')[1]
                subjects.add(subject)
        return sorted(list(subjects))
    
    def get_all_grades(self, subject=None):
        """Get list of all available grades, optionally filtered by subject."""
        grades = set()
        for key in self.standards.keys():
            if '_grade_' in key:
                if subject and not key.endswith(f'_grade_{subject}'):
                    continue
                grade_str = key.split('th_grade_')[0]
                try:
                    grade = int(grade_str)
                    grades.add(grade)
                except ValueError:
                    continue
        return sorted(list(grades))
