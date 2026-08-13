function formatLocation(location = []) {
  return location.filter((part) => part !== "body").join(".");
}

export function parseApiError(error) {
  const data = error.response?.data;

  if (!data) {
    return {
      message: "Unable to reach the ClassFlow API. Check the backend server and API URL.",
      items: [],
    };
  }

  const validationErrors = Array.isArray(data.errors)
    ? data.errors
    : Array.isArray(data.detail)
      ? data.detail
      : [];

  if (validationErrors.length > 0) {
    return {
      message:
        typeof data.detail === "string"
          ? data.detail
          : "Request validation failed",
      items: validationErrors.map((item) => {
        const location = formatLocation(item.loc);
        return location ? `${location}: ${item.msg}` : item.msg;
      }),
    };
  }

  if (typeof data.detail === "string") {
    return {
      message: data.detail,
      items: data.error_code ? [`Code: ${data.error_code}`] : [],
    };
  }

  return {
    message: "Something went wrong. Please try again.",
    items: [],
  };
}
