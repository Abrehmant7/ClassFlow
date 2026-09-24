import { useCallback, useEffect, useRef, useState } from "react";

import { listMyClassrooms } from "../api/classrooms.js";
import { listClassCourses } from "../api/courses.js";
import { canCreateContent, parseContentError } from "../utils/classContent.js";

export default function useClassContent(classId, listContent) {
  const [items, setItems] = useState([]);
  const [classroom, setClassroom] = useState(null);
  const [courses, setCourses] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const requestVersion = useRef(0);

  const load = useCallback(async () => {
    const version = ++requestVersion.current;
    setIsLoading(true);
    setError(null);
    setItems([]);
    try {
      // Content visibility is decided entirely by the content endpoint.
      const [content, classrooms, classCourses] = await Promise.all([
        listContent(classId), listMyClassrooms(), listClassCourses(classId),
      ]);
      if (version !== requestVersion.current) return;
      setItems(content);
      setClassroom(classrooms.find((item) => item.id === classId) || { id: classId });
      setCourses(classCourses);
    } catch (apiError) {
      if (version === requestVersion.current) setError(parseContentError(apiError));
    } finally {
      if (version === requestVersion.current) setIsLoading(false);
    }
  }, [classId, listContent]);

  useEffect(() => {
    load();
    return () => { requestVersion.current += 1; };
  }, [load]);

  function upsert(item) {
    setItems((current) => current.some((entry) => entry.id === item.id)
      ? current.map((entry) => entry.id === item.id ? item : entry)
      : [item, ...current]);
  }

  function remove(id) {
    setItems((current) => current.filter((item) => item.id !== id));
  }

  return {
    items, setItems, classroom, courses, isLoading, error, setError, load, upsert, remove,
    canCreate: !error && canCreateContent(items, classroom?.membership),
  };
}
