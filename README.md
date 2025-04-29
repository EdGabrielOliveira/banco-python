Okay, converting the application to Next.js (App Router), React, TypeScript, and Tailwind CSS is a significant refactoring effort. Here's a structured breakdown with separate components.

**Assumptions:**

*   You have a Next.js project initialized with TypeScript and Tailwind CSS (`npx create-next-app@latest my-eduplanner --typescript --tailwind --eslint --app --src-dir --import-alias "@/*"`).
*   You've installed necessary libraries:
    ```bash
    npm install chart.js react-chartjs-2 @fortawesome/fontawesome-svg-core @fortawesome/free-solid-svg-icons @fortawesome/react-fontawesome
    # or
    yarn add chart.js react-chartjs-2 @fortawesome/fontawesome-svg-core @fortawesome/free-solid-svg-icons @fortawesome/react-fontawesome
    ```

**Project Structure:**

```
src/
├── app/
│   ├── layout.tsx        # Root Layout
│   └── page.tsx          # Main Page Component (Dashboard/Entry)
├── components/
│   ├── ui/               # Generic UI elements (Button, Modal, Input etc. - Optional but good practice)
│   │   ├── Button.tsx
│   │   ├── Modal.tsx
│   │   └── ...
│   ├── layout/           # Layout specific components
│   │   ├── Header.tsx
│   │   ├── MobileMenu.tsx
│   │   └── Sidebar.tsx
│   ├── sections/         # Main content sections
│   │   ├── CalendarSection.tsx
│   │   ├── DashboardSection.tsx
│   │   ├── ProgressSection.tsx
│   │   ├── SubjectsSection.tsx
│   │   └── TasksSection.tsx
│   ├── charts/           # Chart components
│   │   ├── ProductivityHistoryChart.tsx
│   │   ├── TasksBySubjectChart.tsx
│   │   └── WeeklyCompletionChart.tsx
│   ├── modals/           # Modal components
│   │   ├── AddEditSubjectModal.tsx
│   │   ├── AddEditTaskModal.tsx
│   │   └── TaskDetailModal.tsx
│   ├── SubjectCard.tsx
│   ├── TaskItem.tsx
│   └── NotificationBanner.tsx # For displaying notifications
├── context/
│   └── AppContext.tsx    # Context for managing global state (tasks, subjects, etc.)
├── hooks/
│   └── useLocalStorage.ts # Hook for persisting state
├── lib/
│   ├── colors.ts         # Color mapping constants
│   ├── dates.ts          # Date utility functions
│   └── utils.ts          # General utility functions
└── types/
    └── index.ts          # TypeScript type definitions (Task, Subject)
```

---

**1. Types (`src/types/index.ts`)**

```typescript
export type Priority = 'low' | 'medium' | 'high';
export type SubjectColor = 'indigo' | 'blue' | 'green' | 'yellow' | 'red' | 'purple' | 'gray'; // Added gray as default

export interface Subject {
  id: number;
  name: string;
  teacher?: string;
  color: SubjectColor;
}

export interface Task {
  id: number;
  title: string;
  description?: string;
  subjectId: number | null; // Allow null if subject is deleted
  dueDate: string; // Store as YYYY-MM-DD string
  priority: Priority;
  completed: boolean;
  createdAt: string; // Store as YYYY-MM-DD string
}

// Type for the state managed by context
export interface AppState {
  tasks: Task[];
  subjects: Subject[];
  currentTaskId: number;
  currentSubjectId: number;
}

// Type for the context value, including state and actions
export interface AppContextProps extends AppState {
  addTask: (taskData: Omit<Task, 'id' | 'completed' | 'createdAt'>) => void;
  updateTask: (taskId: number, taskData: Partial<Omit<Task, 'id' | 'createdAt'>>) => void;
  deleteTask: (taskId: number) => void;
  toggleTaskCompletion: (taskId: number) => void;
  addSubject: (subjectData: Omit<Subject, 'id'>) => void;
  updateSubject: (subjectId: number, subjectData: Partial<Omit<Subject, 'id'>>) => void;
  deleteSubject: (subjectId: number) => void;
  getSubjectById: (id: number | null) => Subject | undefined;
  getTasksBySubject: (subjectId: number) => Task[];
  getTasksForDate: (dateStr: string) => Task[];
  // Add other necessary functions/state accessors
}

// Type for Modal states
export type ModalType = 'addTask' | 'editTask' | 'addSubject' | 'editSubject' | 'viewTask' | null;

export interface ModalState {
    type: ModalType;
    taskId?: number;
    subjectId?: number;
}

// For notification state
export interface NotificationState {
    message: string;
    type: 'success' | 'error' | 'info';
    visible: boolean;
}
```

---

**2. Local Storage Hook (`src/hooks/useLocalStorage.ts`)**

```typescript
import { useState, useEffect } from 'react';

function useLocalStorage<T>(key: string, initialValue: T): [T, (value: T) => void] {
  // Get from local storage then parse stored json or return initialValue
  const readValue = (): T => {
    // Prevent build errors during server-side rendering
    if (typeof window === 'undefined') {
      return initialValue;
    }
    try {
      const item = window.localStorage.getItem(key);
      return item ? (JSON.parse(item) as T) : initialValue;
    } catch (error) {
      console.warn(`Error reading localStorage key “${key}”:`, error);
      return initialValue;
    }
  };

  const [storedValue, setStoredValue] = useState<T>(readValue);

  // Return a wrapped version of useState's setter function that ...
  // ... persists the new value to localStorage.
  const setValue = (value: T | ((val: T) => T)) => {
    // Prevent build errors during server-side rendering
    if (typeof window === 'undefined') {
      console.warn(
        `Tried setting localStorage key “${key}” even though environment is not a client`
      );
    }
    try {
      // Allow value to be a function so we have same API as useState
      const valueToStore = value instanceof Function ? value(storedValue) : value;
      // Save state
      setStoredValue(valueToStore);
      // Save to local storage
      window.localStorage.setItem(key, JSON.stringify(valueToStore));
    } catch (error) {
      console.warn(`Error setting localStorage key “${key}”:`, error);
    }
  };

   // Read localStorage again if key changes or on mount
   useEffect(() => {
    setStoredValue(readValue());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  return [storedValue, setValue];
}

export default useLocalStorage;
```

---

**3. Context (`src/context/AppContext.tsx`)**

```typescript
'use client'; // This directive is necessary for Context and Hooks

import React, { createContext, useContext, useState, ReactNode, useCallback, useMemo } from 'react';
import { Task, Subject, AppState, AppContextProps, Priority, SubjectColor } from '@/types';
import useLocalStorage from '@/hooks/useLocalStorage';
import { formatDate } from '@/lib/dates'; // Assuming you create this file

// --- Default/Initial State ---
const initialAppState: AppState = {
  tasks: [],
  subjects: [],
  currentTaskId: 1,
  currentSubjectId: 1,
};

// --- Sample Data Loader (only if localStorage is empty) ---
function loadSampleData(): AppState {
    const subjects: Subject[] = [
        { id: 1, name: 'Matemática', teacher: 'Prof. Silva', color: 'indigo' },
        { id: 2, name: 'Português', teacher: 'Prof. Oliveira', color: 'blue' },
        { id: 3, name: 'História', teacher: 'Prof. Santos', color: 'green' },
    ];
    const today = new Date();
    const tomorrow = new Date(today); tomorrow.setDate(today.getDate() + 1);
    const yesterday = new Date(today); yesterday.setDate(today.getDate() - 1);

    const tasks: Task[] = [
        { id: 1, title: 'Exercícios Álgebra', subjectId: 1, dueDate: formatDate(tomorrow), priority: 'high', completed: false, createdAt: formatDate(yesterday) },
        { id: 2, title: 'Redação', subjectId: 2, dueDate: formatDate(today), priority: 'medium', completed: false, createdAt: formatDate(yesterday) },
        { id: 3, title: 'Pesquisa História', subjectId: 3, dueDate: formatDate(yesterday), priority: 'low', completed: true, createdAt: formatDate(yesterday) },
    ];
    return {
        tasks,
        subjects,
        currentTaskId: 4,
        currentSubjectId: 4,
    };
}


// --- Create Context ---
const AppContext = createContext<AppContextProps | undefined>(undefined);

// --- Context Provider Component ---
interface AppProviderProps {
  children: ReactNode;
}

export const AppProvider: React.FC<AppProviderProps> = ({ children }) => {
  const [tasks, setTasks] = useLocalStorage<Task[]>('eduPlannerTasks', []);
  const [subjects, setSubjects] = useLocalStorage<Subject[]>('eduPlannerSubjects', []);
  const [currentTaskId, setCurrentTaskId] = useLocalStorage<number>('eduPlannerTaskId', 1);
  const [currentSubjectId, setCurrentSubjectId] = useLocalStorage<number>('eduPlannerSubjectId', 1);

   // Load sample data if local storage is empty on initial client render
   useState(() => {
    if (typeof window !== 'undefined') {
      const storedTasks = window.localStorage.getItem('eduPlannerTasks');
      const storedSubjects = window.localStorage.getItem('eduPlannerSubjects');
      if (!storedTasks || storedTasks === '[]' || !storedSubjects || storedSubjects === '[]') {
        console.log("Loading sample data...");
        const sample = loadSampleData();
        setTasks(sample.tasks);
        setSubjects(sample.subjects);
        setCurrentTaskId(sample.currentTaskId);
        setCurrentSubjectId(sample.currentSubjectId);
      }
    }
  });

  // --- CRUD Operations ---

  const addTask = useCallback((taskData: Omit<Task, 'id' | 'completed' | 'createdAt'>) => {
    const newTask: Task = {
      ...taskData,
      id: currentTaskId,
      completed: false,
      createdAt: formatDate(new Date()),
    };
    setTasks(prev => [...prev, newTask]);
    setCurrentTaskId(prev => prev + 1);
  }, [currentTaskId, setCurrentTaskId, setTasks]);

  const updateTask = useCallback((taskId: number, taskData: Partial<Omit<Task, 'id' | 'createdAt'>>) => {
    setTasks(prev => prev.map(task =>
      task.id === taskId ? { ...task, ...taskData } : task
    ));
  }, [setTasks]);

  const deleteTask = useCallback((taskId: number) => {
    if (!window.confirm('Tem certeza que deseja excluir esta tarefa?')) return;
    setTasks(prev => prev.filter(task => task.id !== taskId));
  }, [setTasks]);

  const toggleTaskCompletion = useCallback((taskId: number) => {
    setTasks(prev => prev.map(task =>
      task.id === taskId ? { ...task, completed: !task.completed } : task
    ));
  }, [setTasks]);

   const addSubject = useCallback((subjectData: Omit<Subject, 'id'>) => {
    const newSubject: Subject = {
      ...subjectData,
      id: currentSubjectId,
    };
    setSubjects(prev => [...prev, newSubject].sort((a,b) => a.name.localeCompare(b.name))); // Keep sorted
    setCurrentSubjectId(prev => prev + 1);
  }, [currentSubjectId, setCurrentSubjectId, setSubjects]);

  const updateSubject = useCallback((subjectId: number, subjectData: Partial<Omit<Subject, 'id'>>) => {
    setSubjects(prev => prev.map(subject =>
      subject.id === subjectId ? { ...subject, ...subjectData } : subject
    ).sort((a,b) => a.name.localeCompare(b.name))); // Keep sorted
  }, [setSubjects]);

 const deleteSubject = useCallback((subjectId: number) => {
    const subject = subjects.find(s => s.id === subjectId);
    if (!subject) return;
    const tasksUsing = tasks.filter(t => t.subjectId === subjectId).length;
    let confirmMsg = `Tem certeza que deseja excluir a matéria "${subject.name}"?`;
    if (tasksUsing > 0) {
        confirmMsg += `\n\nAVISO: ${tasksUsing} tarefa(s) associada(s) ficará(ão) sem matéria.`;
    }
    if (!window.confirm(confirmMsg)) return;

    setSubjects(prev => prev.filter(subject => subject.id !== subjectId));
    // Update tasks associated with the deleted subject
    setTasks(prev => prev.map(task =>
        task.subjectId === subjectId ? { ...task, subjectId: null } : task
    ));
 }, [subjects, tasks, setSubjects, setTasks]);


  // --- Data Accessors (using useMemo for optimization) ---
  const getSubjectById = useCallback((id: number | null): Subject | undefined => {
    if (id === null) return undefined;
    return subjects.find(subject => subject.id === id);
  }, [subjects]);

  const getTasksBySubject = useCallback((subjectId: number): Task[] => {
      return tasks.filter(task => task.subjectId === subjectId);
  }, [tasks]);

   const getTasksForDate = useCallback((dateStr: string): Task[] => {
       return tasks.filter(task => task.dueDate === dateStr);
   }, [tasks]);

  // --- Context Value ---
  const value = useMemo(() => ({
    tasks,
    subjects,
    currentTaskId,
    currentSubjectId,
    addTask,
    updateTask,
    deleteTask,
    toggleTaskCompletion,
    addSubject,
    updateSubject,
    deleteSubject,
    getSubjectById,
    getTasksBySubject,
    getTasksForDate,
  }), [
      tasks, subjects, currentTaskId, currentSubjectId,
      addTask, updateTask, deleteTask, toggleTaskCompletion,
      addSubject, updateSubject, deleteSubject,
      getSubjectById, getTasksBySubject, getTasksForDate
    ]);

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
};

// --- Custom Hook to use the Context ---
export const useAppContext = (): AppContextProps => {
  const context = useContext(AppContext);
  if (context === undefined) {
    throw new Error('useAppContext must be used within an AppProvider');
  }
  return context;
};
```

---

**4. Root Layout (`src/app/layout.tsx`)**

```typescript
import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css'; // Your Tailwind global styles
import { AppProvider } from '@/context/AppContext'; // Import the provider
import { config } from '@fortawesome/fontawesome-svg-core'
import '@fortawesome/fontawesome-svg-core/styles.css'

// Prevent Font Awesome from adding its CSS since we did it manually above:
config.autoAddCss = false

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'EduPlanner - Gerenciador Escolar',
  description: 'Gerencie suas tarefas e matérias escolares facilmente.',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt-BR">
      <body className={`${inter.className} bg-gray-50 font-sans`}>
        {/* Wrap the entire application with the context provider */}
        <AppProvider>
           {children}
        </AppProvider>
      </body>
    </html>
  );
}
```

---

**5. Main Page (`src/app/page.tsx`)**

This component will manage the overall layout (Sidebar + Main Content) and the currently displayed section. It will also handle modal visibility.

```typescript
'use client';

import React, { useState, useMemo, useCallback } from 'react';
import Sidebar from '@/components/layout/Sidebar';
import Header from '@/components/layout/Header';
import MobileMenu from '@/components/layout/MobileMenu';
import DashboardSection from '@/components/sections/DashboardSection';
import TasksSection from '@/components/sections/TasksSection';
import CalendarSection from '@/components/sections/CalendarSection';
import SubjectsSection from '@/components/sections/SubjectsSection';
import ProgressSection from '@/components/sections/ProgressSection';
import AddEditTaskModal from '@/components/modals/AddEditTaskModal';
import AddEditSubjectModal from '@/components/modals/AddEditSubjectModal';
import TaskDetailModal from '@/components/modals/TaskDetailModal';
import NotificationBanner from '@/components/NotificationBanner';
import { ModalState, NotificationState } from '@/types';

type SectionType = 'dashboard' | 'tasks' | 'calendar' | 'subjects' | 'progress';

export default function Home() {
  const [currentSection, setCurrentSection] = useState<SectionType>('dashboard');
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [modalState, setModalState] = useState<ModalState>({ type: null });
  const [notification, setNotification] = useState<NotificationState>({ message: '', type: 'info', visible: false });

  const handleSectionChange = useCallback((section: SectionType) => {
    setCurrentSection(section);
    setIsMobileMenuOpen(false); // Close mobile menu on section change
  }, []);

  const openModal = useCallback((type: ModalState['type'], taskId?: number, subjectId?: number) => {
      setModalState({ type, taskId, subjectId });
  }, []);

  const closeModal = useCallback(() => {
      setModalState({ type: null });
  }, []);

  const showNotification = useCallback((message: string, type: NotificationState['type'] = 'success', duration: number = 3000) => {
      setNotification({ message, type, visible: true });
      setTimeout(() => {
          setNotification(prev => ({ ...prev, visible: false }));
      }, duration);
  }, []);


  const sectionComponent = useMemo(() => {
    switch (currentSection) {
      case 'tasks':
        return <TasksSection openModal={openModal} showNotification={showNotification} />;
      case 'calendar':
        return <CalendarSection openModal={openModal} showNotification={showNotification} />;
      case 'subjects':
        return <SubjectsSection openModal={openModal} showNotification={showNotification} />;
      case 'progress':
        return <ProgressSection />;
      case 'dashboard':
      default:
        return <DashboardSection onSectionChange={handleSectionChange} openModal={openModal} showNotification={showNotification}/>;
    }
  }, [currentSection, handleSectionChange, openModal, showNotification]);

  const sectionTitle = useMemo(() => {
     const titles: Record<SectionType, string> = {
        dashboard: 'Dashboard', tasks: 'Tarefas', calendar: 'Calendário',
        subjects: 'Matérias', progress: 'Progresso'
     };
     return titles[currentSection];
  }, [currentSection]);

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar currentSection={currentSection} onSectionChange={handleSectionChange} />

      {/* Main content */}
      <div className="flex flex-col flex-1 overflow-hidden">
        <Header sectionTitle={sectionTitle} />

        {/* Content area */}
        <main className="flex-1 overflow-y-auto p-4 md:p-6 bg-gray-50">
          {sectionComponent}
        </main>
      </div>

      {/* Mobile Menu */}
      <MobileMenu
        isOpen={isMobileMenuOpen}
        onClose={() => setIsMobileMenuOpen(false)}
        currentSection={currentSection}
        onSectionChange={handleSectionChange}
      />
       {/* Mobile Menu FAB */}
       <div className="md:hidden fixed bottom-4 right-4 z-30">
            <button
                onClick={() => setIsMobileMenuOpen(true)}
                className="p-3 rounded-full bg-indigo-600 text-white shadow-lg hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
                aria-label="Abrir menu"
            >
                 <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 12h16m-7 6h7"></path></svg>
            </button>
        </div>


      {/* Modals */}
      <AddEditTaskModal
        isOpen={modalState.type === 'addTask' || modalState.type === 'editTask'}
        onClose={closeModal}
        taskId={modalState.type === 'editTask' ? modalState.taskId : undefined}
        showNotification={showNotification}
      />
       <AddEditSubjectModal
        isOpen={modalState.type === 'addSubject' || modalState.type === 'editSubject'}
        onClose={closeModal}
        subjectId={modalState.type === 'editSubject' ? modalState.subjectId : undefined}
        showNotification={showNotification}
      />
       <TaskDetailModal
        isOpen={modalState.type === 'viewTask'}
        onClose={closeModal}
        taskId={modalState.taskId}
        openEditModal={(id) => openModal('editTask', id)}
        showNotification={showNotification}
      />

      {/* Notification Banner */}
      <NotificationBanner
        message={notification.message}
        type={notification.type}
        isVisible={notification.visible}
      />

    </div>
  );
}
```

---

**6. Component Examples:**

*   **`src/components/layout/Sidebar.tsx`:**

    ```typescript
    'use client';
    import React from 'react';
    import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
    import { faHome, faTasks, faCalendarAlt, faBook, faChartLine, faBookOpen } from '@fortawesome/free-solid-svg-icons';
    import { useAppContext } from '@/context/AppContext';
    import { formatDisplayDate } from '@/lib/dates';
    import { getTodayDateOnly } from '@/lib/dates';

    type SectionType = 'dashboard' | 'tasks' | 'calendar' | 'subjects' | 'progress';

    interface SidebarProps {
      currentSection: SectionType;
      onSectionChange: (section: SectionType) => void;
    }

    const Sidebar: React.FC<SidebarProps> = ({ currentSection, onSectionChange }) => {
      const { tasks, getSubjectById } = useAppContext();

      // Find the next upcoming task
       const nextTask = React.useMemo(() => {
            const now = getTodayDateOnly();
            return tasks
                .filter(task => !task.completed && new Date(task.dueDate) >= now)
                .sort((a, b) => new Date(a.dueDate).getTime() - new Date(b.dueDate).getTime())[0];
       }, [tasks]);

       const nextTaskSubject = nextTask ? getSubjectById(nextTask.subjectId) : null;

      const navItems = [
        { id: 'dashboard', label: 'Dashboard', icon: faHome },
        { id: 'tasks', label: 'Tarefas', icon: faTasks },
        { id: 'calendar', label: 'Calendário', icon: faCalendarAlt },
        { id: 'subjects', label: 'Matérias', icon: faBook },
        { id: 'progress', label: 'Progresso', icon: faChartLine },
      ];

      return (
        <div className="hidden md:flex md:flex-shrink-0">
          <div className="flex flex-col w-64 bg-indigo-700 text-white">
            {/* Logo */}
            <div className="flex items-center justify-center h-16 px-4 border-b border-indigo-800">
              <FontAwesomeIcon icon={faBookOpen} className="text-2xl mr-2" />
              <span className="text-xl font-bold">EduPlanner</span>
            </div>

            {/* Navigation */}
            <nav className="flex-grow px-4 py-4 overflow-y-auto">
              <div className="space-y-1">
                {navItems.map((item) => (
                  <button
                    key={item.id}
                    onClick={() => onSectionChange(item.id as SectionType)}
                    className={`flex items-center px-4 py-2 w-full text-sm font-medium rounded-md transition-colors duration-150 ${
                      currentSection === item.id
                        ? 'bg-indigo-800 text-white'
                        : 'text-indigo-100 hover:bg-indigo-800 hover:text-white'
                    }`}
                  >
                    <FontAwesomeIcon icon={item.icon} className="mr-3 w-5 text-center" />
                    {item.label}
                  </button>
                ))}
              </div>
            </nav>

            {/* Next Task Preview */}
             <div className="mt-auto mb-4 px-4">
                <div className="px-4 py-3 bg-indigo-800 rounded-md">
                    <p className="text-sm font-medium">Próxima tarefa</p>
                    <p className="text-xs truncate mt-1" title={nextTask ? `${nextTask.title} (${nextTaskSubject?.name || 'Sem matéria'}) - ${formatDisplayDate(nextTask.dueDate)}` : 'Nenhuma tarefa pendente'}>
                        {nextTask
                            ? `${nextTask.title} (${nextTaskSubject?.name || 'Sem matéria'}) - ${formatDisplayDate(nextTask.dueDate)}`
                            : 'Nenhuma tarefa pendente'}
                    </p>
                </div>
            </div>
          </div>
        </div>
      );
    };

    export default Sidebar;
    ```

*   **`src/components/TaskItem.tsx`:** (Example for the tasks list)

    ```typescript
    import React from 'react';
    import { Task, Subject, Priority } from '@/types';
    import { formatDisplayDate, getTodayDateOnly } from '@/lib/dates';
    import { getPriorityInfo, getSubjectColorInfo } from '@/lib/colors'; // You'll create this

    interface TaskItemProps {
      task: Task;
      subject?: Subject;
      onToggleComplete: (taskId: number) => void;
      onViewDetails: (taskId: number) => void;
      onEdit: (taskId: number) => void;
      onDelete: (taskId: number) => void;
    }

    const TaskItem: React.FC<TaskItemProps> = ({
      task,
      subject,
      onToggleComplete,
      onViewDetails,
      onEdit,
      onDelete,
    }) => {
      const today = getTodayDateOnly();
      const dueDate = new Date(task.dueDate);
      let dueDateClass = 'text-gray-500';
      let dueDateText = formatDisplayDate(task.dueDate);

      if (!task.completed) {
        if (dueDate < today) {
          dueDateClass = 'text-red-500 font-medium';
          dueDateText = `Atrasada (${formatDisplayDate(task.dueDate)})`;
        } else if (dueDate.getTime() === today.getTime()) {
          dueDateClass = 'text-yellow-600 font-medium';
          dueDateText = 'Entrega Hoje';
        }
      } else {
        dueDateText = `Entregue (${formatDisplayDate(task.dueDate)})`;
      }

      const priorityInfo = getPriorityInfo(task.priority);
      const subjectInfo = getSubjectColorInfo(subject?.color);

      const handleCheckboxClick = (e: React.MouseEvent) => {
        e.stopPropagation(); // Prevent triggering other clicks
        onToggleComplete(task.id);
      };

      const handleEditClick = (e: React.MouseEvent) => {
         e.stopPropagation();
         onEdit(task.id);
      }
      const handleDeleteClick = (e: React.MouseEvent) => {
         e.stopPropagation();
         onDelete(task.id);
      }
       const handleDetailsClick = (e: React.MouseEvent) => {
         e.stopPropagation();
         onViewDetails(task.id);
      }


      return (
        <div
          className={`task-item bg-white p-4 rounded-lg border ${
            task.completed ? 'border-gray-200 opacity-70' : 'border-gray-200 hover:border-indigo-300 hover:shadow-sm'
          } transition-all duration-150`}
        >
          <div className="flex items-start gap-3">
            {/* Checkbox */}
            <div className="flex items-center h-5 mt-1 flex-shrink-0">
              <input
                type="checkbox"
                id={`task-check-${task.id}`}
                checked={task.completed}
                onChange={() => onToggleComplete(task.id)} // Use onChange for accessibility
                onClick={handleCheckboxClick} // Keep onClick for stopPropagation if needed, though onChange usually suffices
                className="custom-checkbox" // Reuse the custom checkbox style from original CSS
              />
            </div>

            {/* Task Info */}
            <div className="flex-1 min-w-0">
              <div className="flex flex-col sm:flex-row justify-between items-start gap-2">
                {/* Title and Description */}
                <div className="flex-1 min-w-0">
                  <label
                    htmlFor={`task-check-${task.id}`}
                    className={`font-medium cursor-pointer ${
                      task.completed ? 'line-through text-gray-500' : 'text-gray-800'
                    }`}
                  >
                    {task.title}
                  </label>
                  {task.description && (
                    <p
                      className={`text-sm text-gray-500 mt-1 ${
                        task.completed ? 'line-through' : ''
                      } break-words`}
                    >
                      {task.description}
                    </p>
                  )}
                </div>
                {/* Badges */}
                <div className="flex items-center flex-shrink-0 space-x-2 mt-1 sm:mt-0">
                  {subject && (
                    <span
                      className={`text-xs px-2 py-0.5 rounded-full ${subjectInfo.bg} ${subjectInfo.text}`}
                    >
                      {subject.name}
                    </span>
                  )}
                  <span
                    className={`text-xs px-2 py-0.5 rounded-full ${priorityInfo.bg} ${priorityInfo.text}`}
                  >
                    {priorityInfo.label}
                  </span>
                </div>
              </div>
              {/* Footer: Due Date and Actions */}
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mt-3 gap-2">
                <span className={`text-sm ${dueDateClass}`}>{dueDateText}</span>
                <div className="flex space-x-3 flex-shrink-0">
                  <button onClick={handleDetailsClick} className="text-xs text-indigo-600 hover:underline">
                    Detalhes
                  </button>
                  <button onClick={handleEditClick} className="text-xs text-gray-600 hover:underline">
                    Editar
                  </button>
                  <button onClick={handleDeleteClick} className="text-xs text-red-500 hover:underline">
                    Excluir
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      );
    };

    export default TaskItem;
    ```

*   **`src/lib/colors.ts`:** (Helper for color classes)

    ```typescript
    import { Priority, SubjectColor } from '@/types';

    // Define color mappings matching Tailwind classes
    const SUBJECT_COLOR_MAP: Record<SubjectColor, { bg: string; text: string; base: string }> = {
        indigo: { bg: 'bg-indigo-100', text: 'text-indigo-800', base: '#6366f1' },
        blue:   { bg: 'bg-blue-100',   text: 'text-blue-800',   base: '#3b82f6' },
        green:  { bg: 'bg-green-100',  text: 'text-green-800',  base: '#10b981' },
        yellow: { bg: 'bg-yellow-100', text: 'text-yellow-800', base: '#f59e0b' },
        red:    { bg: 'bg-red-100',    text: 'text-red-800',    base: '#ef4444' },
        purple: { bg: 'bg-purple-100', text: 'text-purple-800', base: '#a855f7' }, // Adjusted purple
        gray:   { bg: 'bg-gray-100',   text: 'text-gray-800',   base: '#6b7280' }
    };

    const PRIORITY_MAP: Record<Priority, { bg: string; text: string; label: string }> = {
        low:    { bg: 'bg-green-100',  text: 'text-green-800', label: 'Baixa' },
        medium: { bg: 'bg-yellow-100', text: 'text-yellow-800', label: 'Média' },
        high:   { bg: 'bg-red-100',    text: 'text-red-800', label: 'Alta' }
    };

    export const getSubjectColorInfo = (color?: SubjectColor) => {
        return SUBJECT_COLOR_MAP[color || 'gray']; // Default to gray if no color
    };

    export const getPriorityInfo = (priority: Priority) => {
        return PRIORITY_MAP[priority] || PRIORITY_MAP['medium']; // Default to medium
    };

    // Function to get base colors for charts
    export const getSubjectBaseColors = (subjects: {color: SubjectColor}[]) : string[] => {
        return subjects.map(s => SUBJECT_COLOR_MAP[s.color]?.base || SUBJECT_COLOR_MAP['gray'].base);
    }
    ```

*   **`src/lib/dates.ts`:** (Date utilities)
    ```typescript
    // Returns date in YYYY-MM-DD format
    export const formatDate = (date: Date | string | number): string => {
        try {
            const d = new Date(date);
            if (isNaN(d.getTime())) throw new Error("Invalid date");
            const year = d.getFullYear();
            const month = (d.getMonth() + 1).toString().padStart(2, '0');
            const day = d.getDate().toString().padStart(2, '0');
            return `${year}-${month}-${day}`;
        } catch (error) {
            console.error("Error formatting date:", date, error);
            return ''; // Return empty string for invalid dates
        }
    };

    // Input YYYY-MM-DD, Output DD/MM/YYYY
    export const formatDisplayDate = (dateStr: string | null | undefined): string => {
        if (!dateStr || !/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) return '-';
        try {
            const [year, month, day] = dateStr.split('-');
            // Basic validation
            if (parseInt(month) < 1 || parseInt(month) > 12 || parseInt(day) < 1 || parseInt(day) > 31) {
                 return '-';
            }
            return `${day}/${month}/${year}`;
        } catch (error) {
             console.error("Error formatting display date:", dateStr, error);
            return '-';
        }
    };

    // Returns today's date with time set to 00:00:00.000
    export const getTodayDateOnly = (): Date => {
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        return today;
    };

    export const getMonthName = (monthIndex: number): string => {
        const monthNames = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
                           'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'];
        return monthNames[monthIndex] || '';
    }
    ```

---

**Next Steps:**

1.  **Implement Remaining Components:** Create the `Header`, `MobileMenu`, `DashboardSection`, `CalendarSection`, `SubjectsSection`, `ProgressSection`, `SubjectCard`, Chart Components, Modal components, and `NotificationBanner` following the same pattern:
    *   Use `useAppContext` to get data and actions.
    *   Pass necessary props down (e.g., `task` data to `TaskItem`, `openModal` callbacks).
    *   Use Tailwind classes for styling.
    *   Use Font Awesome icons.
    *   Implement `react-chartjs-2` for charts, passing data from the context.
2.  **Refine Modals:** Build the modal components (`AddEditTaskModal`, etc.). They will need internal state for form fields and use the context functions (`addTask`, `updateSubject`, etc.) on save. Use a base `Modal` component for structure (handling overlay, centering, close button).
3.  **Styling:** Add the custom checkbox styles and scrollbar styles to `src/app/globals.css`.
4.  **Testing:** Thoroughly test all interactions, CRUD operations, filtering, calendar navigation, and responsive behavior.

This provides a solid foundation for your React/Next.js EduPlanner. Remember to break down the implementation of the remaining components logically. Good luck!
