-- K-Orbit Database Schema
-- Supabase PostgreSQL Database Setup with RLS (Row Level Security)

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector" SCHEMA "extensions";

-- Set timezone
SET timezone TO 'UTC';

-- Create custom types
CREATE TYPE user_role AS ENUM ('learner', 'sme', 'manager', 'admin', 'super_admin');
CREATE TYPE course_status AS ENUM ('draft', 'published', 'archived');
CREATE TYPE enrollment_status AS ENUM ('not_started', 'in_progress', 'completed', 'paused');
CREATE TYPE lesson_type AS ENUM ('video', 'reading', 'quiz', 'interactive', 'assignment');
CREATE TYPE badge_rarity AS ENUM ('common', 'uncommon', 'rare', 'epic', 'legendary');
CREATE TYPE xp_source AS ENUM ('course_completion', 'lesson_completion', 'quiz_completion', 'forum_answer', 'forum_helpful_answer', 'login_streak', 'badge_earned', 'manual');

-- =====================================================
-- CORE TABLES
-- =====================================================

-- Organizations table
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    domain VARCHAR(255),
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- User profiles table (extends Supabase auth.users)
CREATE TABLE profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role user_role DEFAULT 'learner',
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    avatar_url TEXT,
    department VARCHAR(100),
    position VARCHAR(100),
    manager_id UUID REFERENCES profiles(id),
    onboarding_completed BOOLEAN DEFAULT FALSE,
    last_active TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- User activity logs
CREATE TABLE user_activity_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id UUID,
    metadata JSONB DEFAULT '{}',
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- LEARNING CONTENT TABLES
-- =====================================================

-- Courses table
CREATE TABLE courses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    category VARCHAR(100) NOT NULL,
    difficulty_level VARCHAR(20) CHECK (difficulty_level IN ('beginner', 'intermediate', 'advanced')),
    estimated_duration INTEGER NOT NULL, -- in minutes
    tags TEXT[] DEFAULT '{}',
    prerequisites TEXT[] DEFAULT '{}',
    learning_objectives TEXT[] DEFAULT '{}',
    is_mandatory BOOLEAN DEFAULT FALSE,
    auto_enroll_roles user_role[] DEFAULT '{}',
    status course_status DEFAULT 'draft',
    author_id UUID NOT NULL REFERENCES profiles(id),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    thumbnail_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    published_at TIMESTAMP WITH TIME ZONE
);

-- Lessons table
CREATE TABLE lessons (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    course_id UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    lesson_type lesson_type NOT NULL,
    order_index INTEGER NOT NULL,
    duration INTEGER NOT NULL, -- in minutes
    is_required BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(course_id, order_index)
);

-- Course enrollments
CREATE TABLE course_enrollments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    course_id UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    status enrollment_status DEFAULT 'not_started',
    progress_percentage DECIMAL(5,2) DEFAULT 0.00 CHECK (progress_percentage >= 0 AND progress_percentage <= 100),
    current_lesson_id UUID REFERENCES lessons(id),
    completed_lessons UUID[] DEFAULT '{}',
    time_spent INTEGER DEFAULT 0, -- in minutes
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    last_accessed TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(course_id, user_id)
);

-- Lesson progress tracking
CREATE TABLE lesson_progress (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lesson_id UUID NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    enrollment_id UUID NOT NULL REFERENCES course_enrollments(id) ON DELETE CASCADE,
    status VARCHAR(20) DEFAULT 'not_started' CHECK (status IN ('not_started', 'in_progress', 'completed')),
    progress_percentage DECIMAL(5,2) DEFAULT 0.00 CHECK (progress_percentage >= 0 AND progress_percentage <= 100),
    time_spent INTEGER DEFAULT 0, -- in minutes
    completed_at TIMESTAMP WITH TIME ZONE,
    last_accessed TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(lesson_id, user_id)
);

-- Course ratings and reviews
CREATE TABLE course_ratings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    course_id UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
    review TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(course_id, user_id)
);

-- =====================================================
-- GAMIFICATION TABLES
-- =====================================================

-- XP transactions
CREATE TABLE xp_transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    xp_earned INTEGER NOT NULL,
    source xp_source NOT NULL,
    source_id UUID, -- can reference various entities
    description TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Badges definition
CREATE TABLE badges (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    icon_url TEXT,
    criteria JSONB NOT NULL, -- JSON describing how to earn the badge
    xp_reward INTEGER DEFAULT 0,
    rarity badge_rarity DEFAULT 'common',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- User badges (earned badges)
CREATE TABLE user_badges (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    badge_id UUID NOT NULL REFERENCES badges(id) ON DELETE CASCADE,
    earned_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, badge_id)
);

-- =====================================================
-- FORUM TABLES
-- =====================================================

-- Forum questions
CREATE TABLE forum_questions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    tags TEXT[] DEFAULT '{}',
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    course_id UUID REFERENCES courses(id) ON DELETE SET NULL,
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    is_resolved BOOLEAN DEFAULT FALSE,
    view_count INTEGER DEFAULT 0,
    upvotes INTEGER DEFAULT 0,
    downvotes INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Forum answers
CREATE TABLE forum_answers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    question_id UUID NOT NULL REFERENCES forum_questions(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    is_helpful BOOLEAN DEFAULT FALSE,
    is_accepted BOOLEAN DEFAULT FALSE,
    upvotes INTEGER DEFAULT 0,
    downvotes INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Forum votes (for questions and answers)
CREATE TABLE forum_votes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    target_type VARCHAR(20) NOT NULL CHECK (target_type IN ('question', 'answer')),
    target_id UUID NOT NULL,
    vote_type VARCHAR(10) NOT NULL CHECK (vote_type IN ('upvote', 'downvote')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, target_type, target_id)
);

-- =====================================================
-- AI CHAT TABLES
-- =====================================================

-- AI chat conversations
CREATE TABLE ai_conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    summary TEXT,
    message_count INTEGER DEFAULT 0,
    last_message_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- AI chat messages
CREATE TABLE ai_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES ai_conversations(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}', -- can store sources, confidence, tokens, etc.
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- RESOURCE MANAGEMENT TABLES
-- =====================================================

-- File uploads
CREATE TABLE file_uploads (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    filename VARCHAR(255) NOT NULL,
    original_name VARCHAR(255) NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    size_bytes BIGINT NOT NULL,
    url TEXT NOT NULL,
    uploaded_by UUID NOT NULL REFERENCES profiles(id),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    is_processed BOOLEAN DEFAULT FALSE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Knowledge base documents (for vector search)
CREATE TABLE knowledge_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    source_type VARCHAR(50) NOT NULL, -- 'upload', 'course', 'lesson', etc.
    source_id UUID,
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    embedding vector(768), -- Google Gemini embedding dimension
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- ANALYTICS TABLES
-- =====================================================

-- Learning analytics
CREATE TABLE learning_analytics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    course_id UUID REFERENCES courses(id) ON DELETE CASCADE,
    lesson_id UUID REFERENCES lessons(id) ON DELETE CASCADE,
    metric_name VARCHAR(100) NOT NULL,
    metric_value DECIMAL(10,2) NOT NULL,
    metric_unit VARCHAR(50),
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE
);

-- Intervention alerts
CREATE TABLE intervention_alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    alert_type VARCHAR(50) NOT NULL, -- 'low_engagement', 'struggling_learner', 'overdue_course', etc.
    severity VARCHAR(20) DEFAULT 'medium' CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    message TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    is_resolved BOOLEAN DEFAULT FALSE,
    resolved_by UUID REFERENCES profiles(id),
    resolved_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- NOTIFICATION TABLES
-- =====================================================

-- User notifications
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    action_url TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- INDEXES
-- =====================================================

-- Performance indexes
CREATE INDEX idx_profiles_org_id ON profiles(org_id);
CREATE INDEX idx_profiles_role ON profiles(role);
CREATE INDEX idx_profiles_manager_id ON profiles(manager_id);
CREATE INDEX idx_profiles_last_active ON profiles(last_active);

CREATE INDEX idx_courses_org_id ON courses(org_id);
CREATE INDEX idx_courses_author_id ON courses(author_id);
CREATE INDEX idx_courses_status ON courses(status);
CREATE INDEX idx_courses_category ON courses(category);
CREATE INDEX idx_courses_tags ON courses USING GIN(tags);

CREATE INDEX idx_lessons_course_id ON lessons(course_id);
CREATE INDEX idx_lessons_order_index ON lessons(course_id, order_index);

CREATE INDEX idx_course_enrollments_user_id ON course_enrollments(user_id);
CREATE INDEX idx_course_enrollments_course_id ON course_enrollments(course_id);
CREATE INDEX idx_course_enrollments_status ON course_enrollments(status);

CREATE INDEX idx_lesson_progress_user_id ON lesson_progress(user_id);
CREATE INDEX idx_lesson_progress_lesson_id ON lesson_progress(lesson_id);

CREATE INDEX idx_xp_transactions_user_id ON xp_transactions(user_id);
CREATE INDEX idx_xp_transactions_source ON xp_transactions(source);
CREATE INDEX idx_xp_transactions_created_at ON xp_transactions(created_at);

CREATE INDEX idx_user_badges_user_id ON user_badges(user_id);
CREATE INDEX idx_user_badges_badge_id ON user_badges(badge_id);

CREATE INDEX idx_forum_questions_org_id ON forum_questions(org_id);
CREATE INDEX idx_forum_questions_user_id ON forum_questions(user_id);
CREATE INDEX idx_forum_questions_course_id ON forum_questions(course_id);
CREATE INDEX idx_forum_questions_tags ON forum_questions USING GIN(tags);

CREATE INDEX idx_forum_answers_question_id ON forum_answers(question_id);
CREATE INDEX idx_forum_answers_user_id ON forum_answers(user_id);

CREATE INDEX idx_ai_conversations_user_id ON ai_conversations(user_id);
CREATE INDEX idx_ai_messages_conversation_id ON ai_messages(conversation_id);

CREATE INDEX idx_knowledge_documents_org_id ON knowledge_documents(org_id);
CREATE INDEX idx_knowledge_documents_source ON knowledge_documents(source_type, source_id);

-- Vector similarity search index
CREATE INDEX idx_knowledge_documents_embedding ON knowledge_documents USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE INDEX idx_notifications_user_id ON notifications(user_id);
CREATE INDEX idx_notifications_is_read ON notifications(user_id, is_read);
CREATE INDEX idx_notifications_created_at ON notifications(created_at);

-- =====================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- =====================================================

-- Enable RLS on all tables
ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_activity_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE courses ENABLE ROW LEVEL SECURITY;
ALTER TABLE lessons ENABLE ROW LEVEL SECURITY;
ALTER TABLE course_enrollments ENABLE ROW LEVEL SECURITY;
ALTER TABLE lesson_progress ENABLE ROW LEVEL SECURITY;
ALTER TABLE course_ratings ENABLE ROW LEVEL SECURITY;
ALTER TABLE xp_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE badges ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_badges ENABLE ROW LEVEL SECURITY;
ALTER TABLE forum_questions ENABLE ROW LEVEL SECURITY;
ALTER TABLE forum_answers ENABLE ROW LEVEL SECURITY;
ALTER TABLE forum_votes ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE file_uploads ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE learning_analytics ENABLE ROW LEVEL SECURITY;
ALTER TABLE intervention_alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;

-- Helper function to get user's org_id
CREATE OR REPLACE FUNCTION get_user_org_id()
RETURNS UUID
LANGUAGE SQL
STABLE
AS $$
  SELECT org_id FROM profiles WHERE id = auth.uid();
$$;

-- Helper function to check if user has role
CREATE OR REPLACE FUNCTION user_has_role(required_role user_role)
RETURNS BOOLEAN
LANGUAGE SQL
STABLE
AS $$
  SELECT role = required_role OR role = 'admin' OR role = 'super_admin'
  FROM profiles WHERE id = auth.uid();
$$;

-- Organizations policies
CREATE POLICY "Users can view their organization" ON organizations
    FOR SELECT USING (id = get_user_org_id());

CREATE POLICY "Only super_admins can modify organizations" ON organizations
    FOR ALL USING (user_has_role('super_admin'));

-- Profiles policies
CREATE POLICY "Users can view profiles in their organization" ON profiles
    FOR SELECT USING (org_id = get_user_org_id());

CREATE POLICY "Users can update their own profile" ON profiles
    FOR UPDATE USING (id = auth.uid());

CREATE POLICY "Managers and admins can update team member profiles" ON profiles
    FOR UPDATE USING (
        org_id = get_user_org_id() AND (
            user_has_role('admin') OR 
            (user_has_role('manager') AND manager_id = auth.uid())
        )
    );

-- Courses policies
CREATE POLICY "Users can view published courses in their organization" ON courses
    FOR SELECT USING (
        org_id = get_user_org_id() AND (
            status = 'published' OR 
            author_id = auth.uid() OR 
            user_has_role('admin')
        )
    );

CREATE POLICY "SMEs and above can create courses" ON courses
    FOR INSERT WITH CHECK (
        org_id = get_user_org_id() AND 
        author_id = auth.uid() AND
        (user_has_role('sme') OR user_has_role('manager') OR user_has_role('admin'))
    );

CREATE POLICY "Authors and admins can update courses" ON courses
    FOR UPDATE USING (
        org_id = get_user_org_id() AND (
            author_id = auth.uid() OR 
            user_has_role('admin')
        )
    );

-- Lessons policies
CREATE POLICY "Users can view lessons of accessible courses" ON lessons
    FOR SELECT USING (
        course_id IN (
            SELECT id FROM courses WHERE 
                org_id = get_user_org_id() AND (
                    status = 'published' OR 
                    author_id = auth.uid() OR 
                    user_has_role('admin')
                )
        )
    );

CREATE POLICY "Course authors can manage lessons" ON lessons
    FOR ALL USING (
        course_id IN (
            SELECT id FROM courses WHERE 
                org_id = get_user_org_id() AND (
                    author_id = auth.uid() OR 
                    user_has_role('admin')
                )
        )
    );

-- Course enrollments policies
CREATE POLICY "Users can view their own enrollments" ON course_enrollments
    FOR SELECT USING (user_id = auth.uid());

CREATE POLICY "Users can enroll in courses" ON course_enrollments
    FOR INSERT WITH CHECK (
        user_id = auth.uid() AND
        course_id IN (
            SELECT id FROM courses WHERE 
                org_id = get_user_org_id() AND status = 'published'
        )
    );

CREATE POLICY "Users can update their own enrollments" ON course_enrollments
    FOR UPDATE USING (user_id = auth.uid());

-- Forum policies
CREATE POLICY "Users can view forum content in their organization" ON forum_questions
    FOR SELECT USING (org_id = get_user_org_id());

CREATE POLICY "Users can create forum questions" ON forum_questions
    FOR INSERT WITH CHECK (user_id = auth.uid() AND org_id = get_user_org_id());

CREATE POLICY "Users can update their own questions" ON forum_questions
    FOR UPDATE USING (user_id = auth.uid());

CREATE POLICY "Users can view forum answers" ON forum_answers
    FOR SELECT USING (
        question_id IN (
            SELECT id FROM forum_questions WHERE org_id = get_user_org_id()
        )
    );

CREATE POLICY "Users can create forum answers" ON forum_answers
    FOR INSERT WITH CHECK (
        user_id = auth.uid() AND
        question_id IN (
            SELECT id FROM forum_questions WHERE org_id = get_user_org_id()
        )
    );

-- XP transactions policies
CREATE POLICY "Users can view their own XP transactions" ON xp_transactions
    FOR SELECT USING (user_id = auth.uid());

CREATE POLICY "System can create XP transactions" ON xp_transactions
    FOR INSERT WITH CHECK (true); -- Handled by application logic

-- Notifications policies
CREATE POLICY "Users can view their own notifications" ON notifications
    FOR SELECT USING (user_id = auth.uid());

CREATE POLICY "Users can update their own notifications" ON notifications
    FOR UPDATE USING (user_id = auth.uid());

-- =====================================================
-- TRIGGERS AND FUNCTIONS
-- =====================================================

-- Update updated_at timestamp function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_profiles_updated_at BEFORE UPDATE ON profiles FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_courses_updated_at BEFORE UPDATE ON courses FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_lessons_updated_at BEFORE UPDATE ON lessons FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_lesson_progress_updated_at BEFORE UPDATE ON lesson_progress FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_organizations_updated_at BEFORE UPDATE ON organizations FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to calculate user level from XP
CREATE OR REPLACE FUNCTION calculate_user_level(total_xp INTEGER)
RETURNS INTEGER AS $$
BEGIN
    -- Simple level calculation: every 1000 XP = 1 level
    RETURN GREATEST(1, (total_xp / 1000) + 1);
END;
$$ LANGUAGE plpgsql;

-- Function to update course progress when lesson is completed
CREATE OR REPLACE FUNCTION update_course_progress()
RETURNS TRIGGER AS $$
DECLARE
    total_lessons INTEGER;
    completed_lessons INTEGER;
    new_progress DECIMAL(5,2);
    enrollment_record RECORD;
BEGIN
    -- Only proceed if lesson was just completed
    IF NEW.status = 'completed' AND (OLD.status IS NULL OR OLD.status != 'completed') THEN
        -- Get enrollment record
        SELECT * INTO enrollment_record FROM course_enrollments 
        WHERE id = NEW.enrollment_id;
        
        -- Count total lessons in course
        SELECT COUNT(*) INTO total_lessons 
        FROM lessons 
        WHERE course_id = (SELECT course_id FROM lessons WHERE id = NEW.lesson_id);
        
        -- Count completed lessons for this user
        SELECT COUNT(*) INTO completed_lessons 
        FROM lesson_progress lp
        JOIN lessons l ON lp.lesson_id = l.id
        WHERE l.course_id = (SELECT course_id FROM lessons WHERE id = NEW.lesson_id)
        AND lp.user_id = NEW.user_id 
        AND lp.status = 'completed';
        
        -- Calculate new progress percentage
        new_progress := (completed_lessons::DECIMAL / total_lessons::DECIMAL) * 100;
        
        -- Update course enrollment
        UPDATE course_enrollments 
        SET 
            progress_percentage = new_progress,
            status = CASE 
                WHEN new_progress >= 100 THEN 'completed'::enrollment_status
                WHEN new_progress > 0 THEN 'in_progress'::enrollment_status
                ELSE status
            END,
            completed_at = CASE 
                WHEN new_progress >= 100 THEN CURRENT_TIMESTAMP
                ELSE completed_at
            END,
            completed_lessons = array_append(
                COALESCE(completed_lessons, '{}'), 
                NEW.lesson_id::text
            )
        WHERE id = NEW.enrollment_id;
        
        -- Award XP for lesson completion
        INSERT INTO xp_transactions (user_id, xp_earned, source, source_id, description)
        VALUES (
            NEW.user_id, 
            50, -- Base XP for lesson completion
            'lesson_completion', 
            NEW.lesson_id,
            'Completed lesson: ' || (SELECT title FROM lessons WHERE id = NEW.lesson_id)
        );
        
        -- Award bonus XP if course is completed
        IF new_progress >= 100 THEN
            INSERT INTO xp_transactions (user_id, xp_earned, source, source_id, description)
            VALUES (
                NEW.user_id, 
                200, -- Bonus XP for course completion
                'course_completion', 
                (SELECT course_id FROM lessons WHERE id = NEW.lesson_id),
                'Completed course: ' || (SELECT title FROM courses WHERE id = (SELECT course_id FROM lessons WHERE id = NEW.lesson_id))
            );
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for course progress updates
CREATE TRIGGER trigger_update_course_progress
    AFTER INSERT OR UPDATE ON lesson_progress
    FOR EACH ROW EXECUTE FUNCTION update_course_progress();

-- =====================================================
-- INITIAL DATA
-- =====================================================

-- Insert default badges
INSERT INTO badges (name, description, criteria, xp_reward, rarity) VALUES
('First Steps', 'Complete your first lesson', '{"type": "lesson_completion", "target": 1}', 25, 'common'),
('Getting Started', 'Complete your first course', '{"type": "course_completion", "target": 1}', 100, 'common'),
('Knowledge Seeker', 'Complete 5 courses', '{"type": "course_completion", "target": 5}', 250, 'uncommon'),
('Expert Learner', 'Complete 10 courses', '{"type": "course_completion", "target": 10}', 500, 'rare'),
('Helpful Helper', 'Receive 10 helpful votes on forum answers', '{"type": "forum_contribution", "target": 10}', 200, 'uncommon'),
('XP Master', 'Earn 5000 XP', '{"type": "xp_milestone", "target": 5000}', 300, 'rare'),
('Dedication', 'Maintain a 30-day login streak', '{"type": "streak", "target": 30}', 400, 'epic'),
('Overachiever', 'Complete 25 courses', '{"type": "course_completion", "target": 25}', 1000, 'legendary');

-- =====================================================
-- VIEWS FOR ANALYTICS
-- =====================================================

-- User stats view
CREATE VIEW user_stats AS
SELECT 
    p.id as user_id,
    p.full_name,
    p.email,
    p.role,
    p.org_id,
    COALESCE(xp.total_xp, 0) as total_xp,
    calculate_user_level(COALESCE(xp.total_xp, 0)) as level,
    COALESCE(badges.badge_count, 0) as badges_earned,
    COALESCE(courses.completed_courses, 0) as courses_completed,
    COALESCE(courses.in_progress_courses, 0) as courses_in_progress,
    p.last_active
FROM profiles p
LEFT JOIN (
    SELECT user_id, SUM(xp_earned) as total_xp
    FROM xp_transactions
    GROUP BY user_id
) xp ON p.id = xp.user_id
LEFT JOIN (
    SELECT user_id, COUNT(*) as badge_count
    FROM user_badges
    GROUP BY user_id
) badges ON p.id = badges.user_id
LEFT JOIN (
    SELECT 
        user_id,
        COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_courses,
        COUNT(CASE WHEN status = 'in_progress' THEN 1 END) as in_progress_courses
    FROM course_enrollments
    GROUP BY user_id
) courses ON p.id = courses.user_id
WHERE p.deleted_at IS NULL;

-- Course analytics view
CREATE VIEW course_analytics AS
SELECT 
    c.id,
    c.title,
    c.category,
    c.difficulty_level,
    c.author_id,
    c.org_id,
    c.status,
    COALESCE(enrollments.total_enrollments, 0) as total_enrollments,
    COALESCE(enrollments.completed_enrollments, 0) as completed_enrollments,
    COALESCE(ratings.avg_rating, 0) as avg_rating,
    COALESCE(ratings.rating_count, 0) as rating_count,
    c.created_at,
    c.published_at
FROM courses c
LEFT JOIN (
    SELECT 
        course_id,
        COUNT(*) as total_enrollments,
        COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_enrollments
    FROM course_enrollments
    GROUP BY course_id
) enrollments ON c.id = enrollments.course_id
LEFT JOIN (
    SELECT 
        course_id,
        ROUND(AVG(rating), 2) as avg_rating,
        COUNT(*) as rating_count
    FROM course_ratings
    GROUP BY course_id
) ratings ON c.id = ratings.course_id;

-- =====================================================
-- VECTOR SEARCH FUNCTIONS
-- =====================================================

-- Create vector search function for semantic similarity
CREATE OR REPLACE FUNCTION vector_search(
    org_id UUID,
    query_embedding vector(768),
    match_threshold float DEFAULT 0.5,
    match_count int DEFAULT 3
)
RETURNS TABLE (
    title TEXT,
    content TEXT,
    source_type TEXT,
    metadata JSONB,
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        kd.title,
        kd.content,
        kd.source_type,
        kd.metadata,
        1 - (kd.embedding <=> query_embedding) AS similarity
    FROM knowledge_documents kd
    WHERE 
        kd.org_id = vector_search.org_id
        AND kd.embedding IS NOT NULL
        AND 1 - (kd.embedding <=> query_embedding) > match_threshold
    ORDER BY kd.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Grant permissions to authenticated users
GRANT USAGE ON SCHEMA public TO authenticated;
GRANT ALL ON ALL TABLES IN SCHEMA public TO authenticated;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO authenticated;

-- =====================================================
-- COMMENTS
-- =====================================================

COMMENT ON TABLE organizations IS 'Organizations using the K-Orbit platform';
COMMENT ON TABLE profiles IS 'User profiles extending Supabase auth.users';
COMMENT ON TABLE courses IS 'Learning courses created by SMEs';
COMMENT ON TABLE lessons IS 'Individual lessons within courses';
COMMENT ON TABLE course_enrollments IS 'User enrollments in courses';
COMMENT ON TABLE lesson_progress IS 'Progress tracking for individual lessons';
COMMENT ON TABLE xp_transactions IS 'XP points earned by users';
COMMENT ON TABLE badges IS 'Achievement badges available in the system';
COMMENT ON TABLE user_badges IS 'Badges earned by users';
COMMENT ON TABLE forum_questions IS 'Questions posted in the community forum';
COMMENT ON TABLE forum_answers IS 'Answers to forum questions';
COMMENT ON TABLE ai_conversations IS 'AI chat conversations';
COMMENT ON TABLE ai_messages IS 'Messages within AI conversations';
COMMENT ON TABLE knowledge_documents IS 'Documents for vector similarity search';
COMMENT ON TABLE notifications IS 'User notifications';

-- End of schema 