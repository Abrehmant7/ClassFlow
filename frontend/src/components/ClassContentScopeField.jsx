import { formatCourseTitle } from "../utils/courses.js";

function ClassContentScopeField({ id, courses, value, onChange }) {
  return (
    <div>
      <label className="cf-label" htmlFor={id}>Scope</label>
      <select className="cf-input" id={id} name="class_course_id" onChange={onChange} value={value}>
        <option value="">Entire class</option>
        {courses.filter((course) => course.is_active).map((course) => (
          <option key={course.id} value={course.id}>{formatCourseTitle(course.course)}</option>
        ))}
      </select>
    </div>
  );
}

export default ClassContentScopeField;
